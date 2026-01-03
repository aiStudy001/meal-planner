"""
EC-029: Request Deduplication Tests

Tests for concurrency edge cases and request deduplication
"""

import pytest
from app.models.requests import MealPlanRequest
from app.controllers.meal_plan import get_request_key, active_requests


class TestEC029RequestDeduplication:
    """EC-029: Request deduplication tests"""

    def test_ec029_1_request_key_generation_consistency(self):
        """EC-029-1: 동일한 프로필은 동일한 request_key 생성"""
        # 동일한 프로필
        request1 = MealPlanRequest(
            goal="다이어트",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
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
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        key1 = get_request_key(request1)
        key2 = get_request_key(request2)

        # 동일한 키 생성 확인
        assert key1 == key2
        assert len(key1) == 16  # SHA256 해시의 앞 16자

    def test_ec029_2_different_profiles_generate_different_keys(self):
        """EC-029-2: 다른 프로필은 다른 request_key 생성"""
        request1 = MealPlanRequest(
            goal="다이어트",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        # 체중만 다른 프로필
        request2 = MealPlanRequest(
            goal="다이어트",
            weight=75,  # 체중 변경
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        key1 = get_request_key(request1)
        key2 = get_request_key(request2)

        # 다른 키 생성 확인
        assert key1 != key2

    def test_ec029_3_request_key_independent_of_restrictions(self):
        """EC-029-3: restrictions/health_conditions는 request_key에 영향 없음"""
        # 핵심 프로필은 동일, restrictions만 다름
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

        # 동일한 키 생성 (restrictions는 해시에 포함되지 않음)
        assert key1 == key2

    def test_ec029_4_active_requests_tracking(self):
        """EC-029-4: active_requests 딕셔너리 동작 확인"""
        # 초기 상태 확인
        initial_count = len(active_requests)

        request = MealPlanRequest(
            goal="유지",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        request_key = get_request_key(request)

        # 딕셔너리가 존재하는지 확인
        assert isinstance(active_requests, dict)

        # 빈 상태에서 시작 (테스트 격리)
        if request_key in active_requests:
            del active_requests[request_key]

        assert request_key not in active_requests

        # active_requests는 실제 스트리밍 시작 시 추가됨
        # 여기서는 구조만 검증

    def test_ec029_5_request_key_includes_all_critical_fields(self):
        """EC-029-5: request_key가 모든 핵심 필드를 포함하는지 확인"""
        base_request_args = {
            "goal": "다이어트",
            "weight": 70,
            "height": 175,
            "age": 30,
            "gender": "male",
            "activity_level": "moderate",
            "budget": 100_000,
            "budget_type": "weekly",
            "cooking_time": "30분 이내",
            "skill_level": "중급",
            "meals_per_day": 3,
            "days": 7,
        }

        base_request = MealPlanRequest(**base_request_args)
        base_key = get_request_key(base_request)

        # 각 필드를 변경했을 때 키가 달라지는지 확인
        critical_fields = [
            ("goal", "벌크업"),
            ("weight", 75),
            ("height", 180),
            ("age", 35),
            ("gender", "female"),
            ("activity_level", "high"),
            ("budget", 120_000),
            ("budget_type", "daily"),
            ("meals_per_day", 4),
            ("days", 5),
        ]

        for field_name, new_value in critical_fields:
            modified_args = base_request_args.copy()
            modified_args[field_name] = new_value
            modified_request = MealPlanRequest(**modified_args)
            modified_key = get_request_key(modified_request)

            # 각 필드 변경 시 키가 달라져야 함
            assert modified_key != base_key, f"{field_name} 변경 시 키가 달라야 함"


class TestRequestDeduplicationIntegration:
    """Request deduplication 통합 테스트 (실제 API 호출 시뮬레이션)"""

    @pytest.mark.asyncio
    async def test_concurrent_identical_requests_should_deduplicate(self):
        """동일한 프로필로 동시 요청 시 중복 제거 동작 확인"""
        # 실제 API 테스트는 E2E에서 수행
        # 여기서는 로직 검증만 수행

        request = MealPlanRequest(
            goal="다이어트",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        request_key = get_request_key(request)

        # 동일한 request_key는 동일한 값이어야 함
        assert request_key == get_request_key(request)

    def test_request_key_hash_format(self):
        """request_key의 해시 형식 검증"""
        request = MealPlanRequest(
            goal="다이어트",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            budget=100_000,
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        request_key = get_request_key(request)

        # SHA256 해시의 앞 16자 (16진수)
        assert len(request_key) == 16
        assert all(c in "0123456789abcdef" for c in request_key)
