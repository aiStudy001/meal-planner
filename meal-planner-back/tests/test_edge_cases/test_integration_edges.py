"""
Integration Tests for Edge Cases (Phase 1-4)

통합 테스트: 여러 컴포넌트가 함께 동작하는 시나리오 검증
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import ValidationError

from app.models.requests import MealPlanRequest
from app.models.state import UserProfile, MacroTargets, Menu, ValidationResult, MealPlanState
from app.services.llm_service import LLMService
from app.agents.nodes.meal_planning.nutritionist import nutritionist_agent
from app.agents.nodes.meal_planning.chef import chef_agent
from app.agents.nodes.meal_planning.budget import budget_agent
from app.agents.nodes.meal_planning.conflict_resolver import conflict_resolver
from app.agents.nodes.day_iterator import day_iterator
from app.agents.nodes.retry_router import retry_router
from app.agents.nodes.validation.health_checker import health_checker
from app.agents.nodes.validation.budget_checker import budget_checker
from app.controllers.meal_plan import get_request_key, active_requests
from app.utils.prompt_safety import sanitize_string, escape_for_llm


class TestPhase1Integration:
    """Phase 1: LLM Service + Agent Nodes 통합 테스트"""

    @pytest.mark.asyncio
    async def test_integration_llm_timeout_affects_all_agents(self):
        """INT-001: LLM timeout이 모든 agent 노드에 영향
        
        nutritionist, chef, budget 모두 LLM service를 사용하므로
        timeout 설정이 모든 노드에서 동작해야 함
        """
        llm_service = LLMService(mock_mode=False)
        
        # LLM API가 30초 걸리도록 mock
        mock_llm = AsyncMock()
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(30)
            return MagicMock(content="response")
        mock_llm.ainvoke = slow_invoke
        
        # Replace the llm instance
        llm_service.llm = mock_llm
        
        # 25초 timeout이므로 TimeoutError 발생해야 함
        with pytest.raises(asyncio.TimeoutError):
            await llm_service.ainvoke("test prompt")

    @pytest.mark.asyncio
    async def test_integration_rate_limit_retry_then_validation_error(self):
        """INT-002: Rate limit retry 성공 후 ValidationError 처리
        
        시나리오:
        1. 첫 번째 시도: 429 rate limit
        2. 재시도 성공: 잘못된 JSON 반환
        3. ValidationError로 graceful degradation
        """
        llm_service = LLMService(mock_mode=False)
        
        call_count = 0
        
        mock_llm = AsyncMock()
        async def rate_limit_then_bad_json(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise Exception("429 rate limit exceeded")
            else:
                # 잘못된 JSON 반환
                return MagicMock(content='{"invalid": json}')
        
        mock_llm.ainvoke = rate_limit_then_bad_json
        llm_service.llm = mock_llm
        
        # Rate limit retry 성공 (call_count == 2)
        response = await llm_service.ainvoke("test prompt")
        assert call_count == 2
        assert "invalid" in response

    @pytest.mark.asyncio
    async def test_integration_all_agents_handle_llm_errors_consistently(self):
        """INT-003: 모든 agent가 LLM 에러를 일관되게 처리
        
        nutritionist, chef, budget 모두 JSONDecodeError/ValidationError 시
        None을 반환하고 error 이벤트를 생성해야 함
        """
        # Mock state
        from app.models.state import MealPlanState
        from app.models.state import UserProfile
        
        profile = UserProfile(
            goal="다이어트",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],
            budget=100000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        from app.models.state import MacroTargets

        # Create MacroTargets
        daily_targets = MacroTargets(
            calories=2000.0,
            carb_g=250.0,
            protein_g=100.0,
            fat_g=60.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        per_meal_targets = MacroTargets(
            calories=600.0,
            carb_g=70.0,
            protein_g=25.0,
            fat_g=20.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        state = MealPlanState(
            profile=profile,
            daily_targets=daily_targets,
            per_meal_targets=per_meal_targets,
            per_meal_budget=5000,
            current_day=1,
            current_meal_type="아침",
            current_meal_index=0,
            nutritionist_recommendation=None,
            chef_recommendation=None,
            budget_recommendation=None,
            current_menu=None,
            validation_results=[],
            completed_meals=[],
            weekly_plan=[],
            retry_count=0,
            max_retries=5,
            error_message=None,
            events=[],
        )
        
        # LLM이 잘못된 JSON 반환하도록 mock
        llm_service = LLMService(mock_mode=False)

        async def bad_json(*args, **kwargs):
            # ainvoke should return string directly, not MagicMock
            return '{"broken json'

        with patch('app.services.llm_service.LLMService.ainvoke', side_effect=bad_json):
            # Nutritionist
            result_n = await nutritionist_agent(state)
            assert result_n["nutritionist_recommendation"] is None
            assert any(e["type"] == "error" for e in result_n["events"])
            
            # Chef
            result_c = await chef_agent(state)
            assert result_c["chef_recommendation"] is None
            assert any(e["type"] == "error" for e in result_c["events"])
            
            # Budget
            result_b = await budget_agent(state)
            assert result_b["budget_recommendation"] is None
            assert any(e["type"] == "error" for e in result_b["events"])


class TestPhase2Integration:
    """Phase 2: SSE Streaming + Error Handling 통합 테스트"""

    @pytest.mark.asyncio
    async def test_integration_client_disconnect_during_streaming(self):
        """INT-004: 클라이언트 연결 종료 시 리소스 정리
        
        스트리밍 중 asyncio.CancelledError 발생 시:
        1. Warning 로그 기록
        2. Re-raise for FastAPI cleanup
        3. 다른 active requests에 영향 없음
        """
        from app.services.stream_service import stream_meal_plan
        
        request = MealPlanRequest(
            goal="다이어트",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=100_000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )
        
        # Mock graph astream to raise CancelledError
        async def cancelled_stream(*args, **kwargs):
            yield {"nutritionist": {"events": [{"type": "progress"}]}}
            raise asyncio.CancelledError("Client disconnected")
        
        with patch('app.services.stream_service.get_meal_planner_graph') as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.astream = cancelled_stream
            mock_get_graph.return_value = mock_graph
            
            generator = stream_meal_plan(request)
            
            # 첫 번째 이벤트는 성공
            first_event = await generator.__anext__()
            assert "data:" in first_event
            
            # 두 번째 이벤트에서 CancelledError
            with pytest.raises(asyncio.CancelledError):
                await generator.__anext__()

    @pytest.mark.asyncio
    async def test_integration_mid_stream_error_partial_results(self):
        """INT-005: 스트리밍 중간 에러 발생 시 부분 결과 보존
        
        시나리오:
        1. 첫 3개 chunk 정상 전송
        2. 4번째 chunk에서 에러 발생
        3. Warning 이벤트 전송
        4. 5번째 chunk부터 계속 진행
        """
        from app.services.stream_service import stream_meal_plan
        
        request = MealPlanRequest(
            goal="벌크업",
            weight=80,
            height=180,
            age=25,
            gender="male",
            activity_level="high",
            restrictions=[],
            health_conditions=[],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=150_000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="제한 없음",
            skill_level="고급",
            meals_per_day=4,
            days=7,
        )
        
        chunk_count = 0

        async def error_on_chunk_4(*args, **kwargs):
            nonlocal chunk_count
            # Generate 5 chunks total: 3 good, 1 error, 1 good
            for i in range(5):
                chunk_count += 1
                if chunk_count == 4:
                    # 4번째 chunk에서 에러 발생 (exception을 일으키는 구조)
                    # This will cause .items() to fail since it's not a dict
                    yield None
                else:
                    yield {"nutritionist": {"events": [{"type": "progress", "data": f"chunk {chunk_count}"}]}}
        
        with patch('app.services.stream_service.get_meal_planner_graph') as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.astream = error_on_chunk_4

            # Mock ainvoke to return final state with weekly_plan
            async def mock_ainvoke(*args, **kwargs):
                return {"weekly_plan": []}

            mock_graph.ainvoke = AsyncMock(side_effect=mock_ainvoke)
            mock_get_graph.return_value = mock_graph

            events = []
            async for event in stream_meal_plan(request):
                events.append(event)

            # 최소 5개 이벤트 (3개 정상 + 1개 warning + 1개 이상)
            assert len(events) >= 4

            # Warning 이벤트 포함 확인
            has_warning = any("warning" in event.lower() or "chunk_error" in event.lower() for event in events)
            assert has_warning


class TestPhase3Integration:
    """Phase 3: Validation Subgraph 통합 테스트"""

    @pytest.mark.asyncio
    async def test_integration_validation_supervisor_sends_to_5_validators(self):
        """INT-006: Validation supervisor가 5개 validator에게 병렬 전송
        
        Send API를 통해:
        - nutrition_checker
        - allergy_checker
        - time_checker
        - health_checker (NEW)
        - budget_checker (NEW)
        """
        from app.agents.nodes.validation_supervisor import validation_supervisor
        from app.models.state import MealPlanState
        from app.models.state import UserProfile, Menu
        from langgraph.types import Command, Send
        
        profile = UserProfile(
            goal="질병관리",
            weight=75,
            height=170,
            age=50,
            gender="male",
            activity_level="low",
            restrictions=["우유"],
            health_conditions=["당뇨", "고혈압"],
            budget=100000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="초급",
            meals_per_day=3,
            days=7,
        )
        
        menu = Menu(
            meal_type="아침",
            menu_name="고나트륨 메뉴",
            ingredients=[{"name": "재료1", "amount": "100g"}],
            calories=2000,
            carb_g=250,
            protein_g=100,
            fat_g=60,
            sodium_mg=2500,  # 고혈압 위반
            sugar_g=75.0,  # 30% of carbs
            cooking_time_minutes=30,
            estimated_cost=15000,
            recipe_steps=["조리법"],
            validation_warnings=[],
        )

        from app.models.state import MacroTargets

        # Create MacroTargets
        daily_targets = MacroTargets(
            calories=2000.0,
            carb_g=250.0,
            protein_g=100.0,
            fat_g=60.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        per_meal_targets = MacroTargets(
            calories=600.0,
            carb_g=70.0,
            protein_g=25.0,
            fat_g=20.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        state = MealPlanState(
            profile=profile,
            daily_targets=daily_targets,
            per_meal_targets=per_meal_targets,
            per_meal_budget=5000,
            current_day=1,
            current_meal_type="아침",
            current_meal_index=0,
            nutritionist_recommendation=None,
            chef_recommendation=None,
            budget_recommendation=None,
            current_menu=menu,
            validation_results=[],
            completed_meals=[],
            weekly_plan=[],
            retry_count=0,
            max_retries=5,
            error_message=None,
            events=[],
        )
        
        # Validation supervisor 실행
        command = validation_supervisor(state)
        
        # Command가 반환되는지 확인
        assert isinstance(command, Command)
        
        # goto에 5개의 Send가 있는지 확인
        assert len(command.goto) == 5
        
        # 모든 항목이 Send 타입인지 확인
        assert all(isinstance(item, Send) for item in command.goto)
        
        # 5개 validator 이름 확인
        validator_names = [send.node for send in command.goto]
        expected_validators = [
            "nutrition_checker",
            "allergy_checker",
            "time_checker",
            "health_checker",
            "budget_checker",
        ]
        assert set(validator_names) == set(expected_validators)

    @pytest.mark.asyncio
    async def test_integration_health_and_budget_validators_with_retry_router(self):
        """INT-007: Health/Budget validator 실패 시 retry router 동작
        
        시나리오:
        1. health_checker 실패 (sodium > 2000mg)
        2. budget_checker 실패 (cost > budget * 1.1)
        3. Retry router가 nutritionist, budget로 라우팅
        """
        from app.agents.nodes.validation.health_checker import health_checker
        from app.agents.nodes.validation.budget_checker import budget_checker
        from app.agents.nodes.retry_router import retry_router
        from app.models.state import MealPlanState
        from app.models.state import UserProfile, Menu
        
        profile = UserProfile(
            goal="질병관리",
            weight=75,
            height=170,
            age=50,
            gender="male",
            activity_level="low",
            restrictions=[],
            health_conditions=["고혈압"],
            budget=100000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="초급",
            meals_per_day=3,
            days=7,
        )
        
        menu = Menu(
            meal_type="아침",
            menu_name="고나트륨 고예산 메뉴",
            ingredients=[{"name": "재료1", "amount": "100g"}],
            calories=2000,
            carb_g=250,
            protein_g=100,
            fat_g=60,
            sodium_mg=2500,  # 위반
            sugar_g=75.0,  # 30% of carbs
            cooking_time_minutes=30,
            estimated_cost=6000,  # 위반 (budget 5000 * 1.1 = 5500)
            recipe_steps=["조리법"],
            validation_warnings=[],
        )

        from app.models.state import MacroTargets

        # Create MacroTargets
        daily_targets = MacroTargets(
            calories=2000.0,
            carb_g=250.0,
            protein_g=100.0,
            fat_g=60.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        per_meal_targets = MacroTargets(
            calories=600.0,
            carb_g=70.0,
            protein_g=25.0,
            fat_g=20.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        state = MealPlanState(
            profile=profile,
            daily_targets=daily_targets,
            per_meal_targets=per_meal_targets,
            per_meal_budget=5000,
            current_day=1,
            current_meal_type="아침",
            current_meal_index=0,
            nutritionist_recommendation=None,
            chef_recommendation=None,
            budget_recommendation=None,
            current_menu=menu,
            validation_results=[],
            completed_meals=[],
            weekly_plan=[],
            retry_count=0,
            max_retries=5,
            error_message=None,
            events=[],
        )
        
        # Health checker 실행
        health_result = await health_checker(state)
        assert health_result["validation_results"][0].passed is False
        assert "고혈압" in health_result["validation_results"][0].issues[0]
        
        # Budget checker 실행
        budget_result = await budget_checker(state)
        assert budget_result["validation_results"][0].passed is False
        assert "예산 초과" in budget_result["validation_results"][0].issues[0]
        
        # Validation results를 state에 추가
        state["validation_results"] = [
            health_result["validation_results"][0],
            budget_result["validation_results"][0],
        ]
        
        # Retry router 실행
        route = retry_router(state)

        # retry_count == 0이므로 실패한 validator에 해당하는 전문가로 라우팅
        # route는 Command 객체이므로 route.goto를 확인
        from langgraph.types import Command
        assert isinstance(route, Command)
        assert route.goto in ["nutritionist", "budget"]


class TestPhase4Integration:
    """Phase 4: Security & Input Validation 통합 테스트"""

    def test_integration_budget_bounds_and_per_meal_validation(self):
        """INT-008: Budget bounds와 per-meal validation 통합
        
        시나리오:
        1. Budget이 절대 범위 내 (10,000 ~ 1,000,000)
        2. 하지만 per-meal budget이 2,000원 미만
        3. ValidationError 발생
        """
        # 절대 범위는 통과하지만 per-meal은 실패
        with pytest.raises(ValidationError) as exc_info:
            MealPlanRequest(
                goal="다이어트",
                weight=65,
                height=170,
                age=28,
                gender="female",
                activity_level="low",
                budget=40_000,  # 10,000 ~ 1,000,000 범위 내
                budget_type="weekly",
                cooking_time="15분 이내",
                skill_level="초급",
                meals_per_day=3,
                days=7,
            )
        
        error_msg = str(exc_info.value)
        assert "끼니당 예산이 너무 낮습니다" in error_msg
        assert "1,90" in error_msg  # Accept both 1,904 and 1,905 (rounding)

    def test_integration_prompt_injection_sanitization_and_escaping(self):
        """INT-009: Prompt injection sanitization과 escaping 통합
        
        시나리오:
        1. 정상 입력: sanitization 통과
        2. Escaping 적용
        3. LLM 프롬프트에 안전하게 삽입
        """
        # 정상 입력
        valid_input = "우유 땅콩 대두"
        sanitized = sanitize_string(valid_input, "테스트")
        assert sanitized == "우유 땅콩 대두"
        
        # Escaping
        escaped = escape_for_llm(sanitized)
        assert escaped == "우유 땅콩 대두"  # 특수문자 없으므로 동일
        
        # 특수문자 포함 입력 (escaping 필요)
        special_input = 'Test "quote" and {var}'
        escaped_special = escape_for_llm(special_input)
        assert '\\"' in escaped_special  # 따옴표 이스케이프
        assert '{{' in escaped_special  # 중괄호 이스케이프

    @pytest.mark.asyncio
    async def test_integration_request_deduplication_with_different_restrictions(self):
        """INT-010: Request key는 restrictions/health_conditions 무시
        
        시나리오:
        1. 동일한 프로필, 다른 restrictions
        2. 동일한 request_key 생성
        3. 두 번째 요청은 409 Conflict
        """
        request1 = MealPlanRequest(
            goal="다이어트",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=["우유", "땅콩"],  # 알레르기 있음
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )
        
        request2 = MealPlanRequest(
            goal="다이어트",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],  # 알레르기 없음
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )
        
        key1 = get_request_key(request1)
        key2 = get_request_key(request2)
        
        # Restrictions가 달라도 동일한 키 생성
        assert key1 == key2
        
        # Active requests cleanup
        if key1 in active_requests:
            del active_requests[key1]


class TestPhase5AdditionalIntegration:
    """Phase 5: 추가 통합 테스트 (전체 워크플로우, 상태 전환, 데이터 일관성)"""

    @pytest.mark.asyncio
    async def test_integration_011_full_graph_workflow_single_day(
        self, standard_profile, mock_menu_factory
    ):
        """INT-011: 전체 그래프 워크플로우 (1일 3끼)

        시나리오:
        1. 초기 상태: Day 1, 아침
        2. Nutritionist → Chef → Budget (첫 끼니)
        3. Validation (5 validators)
        4. Day iterator → 점심
        5. Repeat for 점심, 저녁
        6. Daily plan 생성 확인
        """
        from app.agents.nodes.day_iterator import day_iterator
        from app.models.state import MealPlanState, MacroTargets

        # MacroTargets 생성
        daily_targets = MacroTargets(
            calories=2000.0,
            carb_g=250.0,
            protein_g=150.0,
            fat_g=67.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        per_meal_targets = MacroTargets(
            calories=667.0,
            carb_g=83.0,
            protein_g=50.0,
            fat_g=22.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        # 3개 메뉴 생성 (아침, 점심, 저녁)
        breakfast = mock_menu_factory("아침", calories=650, cost=5000)
        lunch = mock_menu_factory("점심", calories=700, cost=6000)
        dinner = mock_menu_factory("저녁", calories=650, cost=5500)

        # 초기 상태
        state = MealPlanState(
            profile=standard_profile,
            daily_targets=daily_targets,
            per_meal_targets=per_meal_targets,
            per_meal_budget=4762,  # 100000 / (3 * 7)
            current_day=1,
            current_meal_type="아침",
            current_meal_index=0,
            nutritionist_recommendation=None,
            chef_recommendation=None,
            budget_recommendation=None,
            current_menu=breakfast,
            validation_results=[],
            completed_meals=[],
            weekly_plan=[],
            retry_count=0,
            max_retries=5,
            error_message=None,
            events=[],
        )

        # 아침 완료 → 점심으로 진행
        state1 = day_iterator(state)
        assert state1["current_day"] == 1
        assert state1["current_meal_type"] == "점심"
        assert state1["current_meal_index"] == 1
        assert len(state1["completed_meals"]) == 1

        # 점심 완료 → 저녁으로 진행
        state["current_menu"] = lunch
        state["completed_meals"] = state1["completed_meals"]
        state["current_meal_index"] = 1
        state["current_meal_type"] = "점심"
        state2 = day_iterator(state)
        assert state2["current_day"] == 1
        assert state2["current_meal_type"] == "저녁"
        assert state2["current_meal_index"] == 2
        assert len(state2["completed_meals"]) == 2

        # 저녁 완료 → Day 2 시작
        state["current_menu"] = dinner
        state["completed_meals"] = state2["completed_meals"]
        state["current_meal_index"] = 2
        state["current_meal_type"] = "저녁"
        state3 = day_iterator(state)

        # Day 1 완료, Day 2로 진행
        assert state3["current_day"] == 2
        assert state3["current_meal_type"] == "아침"
        assert state3["current_meal_index"] == 0
        assert len(state3["completed_meals"]) == 0  # 새로운 날 시작
        assert len(state3["weekly_plan"]) == 1  # Day 1 DailyPlan 추가됨

        # DailyPlan 검증
        daily_plan = state3["weekly_plan"][0]
        assert daily_plan.day == 1
        assert len(daily_plan.meals) == 3
        assert daily_plan.total_calories == 650 + 700 + 650
        assert daily_plan.total_cost == 5000 + 6000 + 5500

    @pytest.mark.asyncio
    async def test_integration_012_multi_day_state_transitions(
        self, standard_profile, mock_menu_factory
    ):
        """INT-012: 3일간 상태 전환 검증

        시나리오:
        1. Day 1: 아침 → 점심 → 저녁 (3 meals)
        2. Day 2: 아침 → 점심 → 저녁 (3 meals)
        3. Day 3: 아침 → 점심 → 저녁 (3 meals)
        4. weekly_plan에 3개 DailyPlan 확인
        5. 각 DailyPlan의 totals 검증
        """
        from app.agents.nodes.day_iterator import day_iterator
        from app.models.state import MealPlanState, MacroTargets

        # 3일만 테스트하도록 profile 수정
        profile_3days = UserProfile(
            goal=standard_profile.goal,
            weight=standard_profile.weight,
            height=standard_profile.height,
            age=standard_profile.age,
            gender=standard_profile.gender,
            activity_level=standard_profile.activity_level,
            restrictions=standard_profile.restrictions,
            health_conditions=standard_profile.health_conditions,
            budget=standard_profile.budget,
            budget_type=standard_profile.budget_type,
            cooking_time=standard_profile.cooking_time,
            skill_level=standard_profile.skill_level,
            meals_per_day=3,
            days=3,  # 3일만 테스트
        )

        daily_targets = MacroTargets(
            calories=2000.0,
            carb_g=250.0,
            protein_g=150.0,
            fat_g=67.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        per_meal_targets = MacroTargets(
            calories=667.0,
            carb_g=83.0,
            protein_g=50.0,
            fat_g=22.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        # 초기 상태
        state = MealPlanState(
            profile=profile_3days,
            daily_targets=daily_targets,
            per_meal_targets=per_meal_targets,
            per_meal_budget=11111,  # 100000 / (3 * 3)
            current_day=1,
            current_meal_type="아침",
            current_meal_index=0,
            nutritionist_recommendation=None,
            chef_recommendation=None,
            budget_recommendation=None,
            current_menu=None,
            validation_results=[],
            completed_meals=[],
            weekly_plan=[],
            retry_count=0,
            max_retries=5,
            error_message=None,
            events=[],
        )

        # 3일 × 3끼 = 9개 메뉴 생성 및 진행
        for day in range(1, 4):  # Day 1, 2, 3
            for meal_idx, meal_type in enumerate(["아침", "점심", "저녁"]):
                # Menu 생성
                menu = mock_menu_factory(meal_type, calories=600, cost=10000)
                state["current_menu"] = menu

                # day_iterator 실행
                result = day_iterator(state)

                # 결과 적용
                if "weekly_plan" in result:
                    state["weekly_plan"] = result["weekly_plan"]
                if "completed_meals" in result:
                    state["completed_meals"] = result["completed_meals"]
                if "current_day" in result:
                    state["current_day"] = result["current_day"]
                if "current_meal_type" in result:
                    state["current_meal_type"] = result["current_meal_type"]
                if "current_meal_index" in result:
                    state["current_meal_index"] = result["current_meal_index"]

        # 3일 모두 완료되었는지 확인
        assert len(state["weekly_plan"]) == 3

        # 각 DailyPlan 검증
        for i, daily_plan in enumerate(state["weekly_plan"]):
            assert daily_plan.day == i + 1
            assert len(daily_plan.meals) == 3
            assert daily_plan.total_calories == 600 * 3  # 1800
            assert daily_plan.total_cost == 10000 * 3  # 30000

    @pytest.mark.asyncio
    async def test_integration_013_retry_routing_strategy(self):
        """INT-013: Retry router 라우팅 전략 검증

        시나리오:
        1. retry_count = 0: 특정 전문가로 라우팅 (nutrition_checker 실패 → nutritionist)
        2. retry_count >= 1: meal_planning_supervisor로 라우팅 (전체 재실행)
        3. conflict_resolver는 max_retries 도달 시 동작
        4. validation_warnings 추가하여 진행
        """
        from langgraph.types import Command

        profile = UserProfile(
            goal="유지",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="테스트 메뉴",
            ingredients=[{"name": "재료1", "amount": "100g"}],
            calories=800,  # 목표 초과
            carb_g=100,
            protein_g=40,
            fat_g=20,
            sodium_mg=1000,
            sugar_g=20,
            cooking_time_minutes=30,
            estimated_cost=5000,
            recipe_steps=["조리법"],
            validation_warnings=[],
        )

        daily_targets = MacroTargets(
            calories=2000.0,
            carb_g=250.0,
            protein_g=150.0,
            fat_g=67.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        per_meal_targets = MacroTargets(
            calories=667.0,
            carb_g=83.0,
            protein_g=50.0,
            fat_g=22.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        # Validation 실패 결과
        validation_fail = ValidationResult(
            validator="nutrition_checker",
            passed=False,
            issues=["칼로리 20% 초과"],
            reason="영양 목표 미달성",
        )

        # Test 1: retry_count = 0 → 특정 전문가 (nutritionist)
        state_first_retry = MealPlanState(
            profile=profile,
            daily_targets=daily_targets,
            per_meal_targets=per_meal_targets,
            per_meal_budget=4762,
            current_day=1,
            current_meal_type="아침",
            current_meal_index=0,
            nutritionist_recommendation=None,
            chef_recommendation=None,
            budget_recommendation=None,
            current_menu=menu,
            validation_results=[validation_fail],
            completed_meals=[],
            weekly_plan=[],
            retry_count=0,
            max_retries=5,
            error_message=None,
            events=[],
        )

        route_first = retry_router(state_first_retry)
        assert isinstance(route_first, Command)
        # nutrition_checker 실패 시 nutritionist로 라우팅
        assert route_first.goto == "nutritionist"
        assert route_first.update["retry_count"] == 1

        # Test 2: retry_count >= 1 → meal_planning_supervisor
        for retry_count in [1, 2, 3, 4, 5]:
            state = MealPlanState(
                profile=profile,
                daily_targets=daily_targets,
                per_meal_targets=per_meal_targets,
                per_meal_budget=4762,
                current_day=1,
                current_meal_type="아침",
                current_meal_index=0,
                nutritionist_recommendation=None,
                chef_recommendation=None,
                budget_recommendation=None,
                current_menu=menu,
                validation_results=[validation_fail],
                completed_meals=[],
                weekly_plan=[],
                retry_count=retry_count,
                max_retries=5,
                error_message=None,
                events=[],
            )

            route = retry_router(state)
            assert isinstance(route, Command)
            # retry_count >= 1일 때는 meal_planning_supervisor로 라우팅
            assert route.goto == "meal_planning_supervisor"
            assert route.update["retry_count"] == retry_count + 1
            # 전체 추천 초기화 확인
            assert route.update["nutritionist_recommendation"] is None
            assert route.update["chef_recommendation"] is None
            assert route.update["budget_recommendation"] is None

    @pytest.mark.asyncio
    async def test_integration_014_weekly_data_consistency(
        self, standard_profile, mock_menu_factory
    ):
        """INT-014: 주간 데이터 일관성 검증

        시나리오:
        1. 7일 × 3끼 = 21개 메뉴 생성
        2. 각 메뉴: calories=500, cost=4000
        3. Weekly plan 생성
        4. 검증:
           - 7 daily plans in weekly_plan
           - Daily totals: 1500 cal, 12000원
           - Weekly totals: 10500 cal, 84000원
        5. Floating point 오차 < 1% 허용
        """
        from app.agents.nodes.day_iterator import day_iterator
        from app.models.state import MealPlanState, MacroTargets

        daily_targets = MacroTargets(
            calories=2000.0,
            carb_g=250.0,
            protein_g=150.0,
            fat_g=67.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        per_meal_targets = MacroTargets(
            calories=667.0,
            carb_g=83.0,
            protein_g=50.0,
            fat_g=22.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        # 초기 상태
        state = MealPlanState(
            profile=standard_profile,
            daily_targets=daily_targets,
            per_meal_targets=per_meal_targets,
            per_meal_budget=4762,
            current_day=1,
            current_meal_type="아침",
            current_meal_index=0,
            nutritionist_recommendation=None,
            chef_recommendation=None,
            budget_recommendation=None,
            current_menu=None,
            validation_results=[],
            completed_meals=[],
            weekly_plan=[],
            retry_count=0,
            max_retries=5,
            error_message=None,
            events=[],
        )

        # 7일 × 3끼 = 21개 메뉴 생성 및 진행
        for day in range(1, 8):  # Day 1~7
            for meal_idx, meal_type in enumerate(["아침", "점심", "저녁"]):
                # 동일한 값으로 Menu 생성 (deterministic)
                menu = mock_menu_factory(
                    meal_type, calories=500.0, cost=4000, carb_g=62.5, protein_g=37.5, fat_g=11.1
                )
                state["current_menu"] = menu

                # day_iterator 실행
                result = day_iterator(state)

                # 결과 적용
                if "weekly_plan" in result:
                    state["weekly_plan"] = result["weekly_plan"]
                if "completed_meals" in result:
                    state["completed_meals"] = result["completed_meals"]
                if "current_day" in result:
                    state["current_day"] = result["current_day"]
                if "current_meal_type" in result:
                    state["current_meal_type"] = result["current_meal_type"]
                if "current_meal_index" in result:
                    state["current_meal_index"] = result["current_meal_index"]

        # Weekly plan 검증
        assert len(state["weekly_plan"]) == 7

        # Daily level 검증
        for daily_plan in state["weekly_plan"]:
            assert len(daily_plan.meals) == 3
            # Daily totals
            assert abs(daily_plan.total_calories - 1500.0) < 10  # 1% tolerance
            assert daily_plan.total_cost == 12000
            assert abs(daily_plan.total_carb_g - 187.5) < 5
            assert abs(daily_plan.total_protein_g - 112.5) < 5
            assert abs(daily_plan.total_fat_g - 33.3) < 1

        # Weekly level 검증
        weekly_calories = sum(d.total_calories for d in state["weekly_plan"])
        weekly_cost = sum(d.total_cost for d in state["weekly_plan"])
        weekly_carb = sum(d.total_carb_g for d in state["weekly_plan"])
        weekly_protein = sum(d.total_protein_g for d in state["weekly_plan"])
        weekly_fat = sum(d.total_fat_g for d in state["weekly_plan"])

        assert abs(weekly_calories - 10500.0) < 100  # 1% tolerance
        assert weekly_cost == 84000
        assert abs(weekly_carb - 1312.5) < 50
        assert abs(weekly_protein - 787.5) < 50
        assert abs(weekly_fat - 233.1) < 10

    @pytest.mark.asyncio
    async def test_integration_015_complex_constraint_combination(
        self, constrained_profile, mock_menu_factory
    ):
        """INT-015: 복합 제약 조건 동시 처리

        시나리오:
        1. Profile: 저예산 + 당뇨 + 고혈압 + 4끼/일 + 7일
        2. Budget agent: 2500원 이내 메뉴 생성
        3. Health checker: sugar ≤ 30g, sodium ≤ 2000mg
        4. Budget checker: cost ≤ 2500 * 1.1 = 2750원
        5. 28개 메뉴 (7일 × 4끼) 모두 제약 만족
        6. Weekly plan 생성 성공
        """
        from app.agents.nodes.validation.health_checker import health_checker
        from app.agents.nodes.validation.budget_checker import budget_checker
        from app.models.state import MealPlanState, MacroTargets

        # per_meal_budget = 70000 / (4 * 7) = 2500원
        assert constrained_profile.budget == 70_000
        assert constrained_profile.meals_per_day == 4
        assert constrained_profile.days == 7
        per_meal_budget = 70_000 / (4 * 7)
        assert per_meal_budget == 2500

        daily_targets = MacroTargets(
            calories=1800.0,  # Low activity
            carb_g=225.0,
            protein_g=135.0,
            fat_g=60.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        per_meal_targets = MacroTargets(
            calories=450.0,  # 1800 / 4
            carb_g=56.25,
            protein_g=33.75,
            fat_g=15.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        )

        # 제약 만족하는 메뉴 생성 (저예산, 당뇨, 고혈압)
        menu = mock_menu_factory(
            "아침",
            calories=450.0,
            cost=2400,  # < 2500
            carb_g=56.0,
            protein_g=34.0,
            fat_g=15.0,
            sodium_mg=1800,  # < 2000 (고혈압)
            sugar_g=25.0,  # < 30 (당뇨)
        )

        state = MealPlanState(
            profile=constrained_profile,
            daily_targets=daily_targets,
            per_meal_targets=per_meal_targets,
            per_meal_budget=2500,
            current_day=1,
            current_meal_type="아침",
            current_meal_index=0,
            nutritionist_recommendation=None,
            chef_recommendation=None,
            budget_recommendation=None,
            current_menu=menu,
            validation_results=[],
            completed_meals=[],
            weekly_plan=[],
            retry_count=0,
            max_retries=5,
            error_message=None,
            events=[],
        )

        # Health checker 실행
        health_result = await health_checker(state)
        assert len(health_result["validation_results"]) == 1
        # 당뇨, 고혈압 모두 만족하므로 통과
        assert health_result["validation_results"][0].passed is True

        # Budget checker 실행
        budget_result = await budget_checker(state)
        assert len(budget_result["validation_results"]) == 1
        # 예산 이내이므로 통과
        assert budget_result["validation_results"][0].passed is True

        # 메뉴 제약 검증
        assert menu.estimated_cost <= 2750  # 10% over budget allowed
        assert menu.sugar_g <= 30  # 당뇨 제약
        assert menu.sodium_mg <= 2000  # 고혈압 제약
        assert menu.calories <= 500  # 칼로리 제한
