"""그래프 실행 테스트"""
import pytest
from app.models.state import UserProfile, MealPlanState
from app.agents.graphs.main_graph import get_meal_planner_graph
from app.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="module", autouse=True)
def setup_test_logging():
    """테스트용 로깅 설정"""
    setup_logging("INFO")


@pytest.fixture
def sample_profile() -> UserProfile:
    """샘플 사용자 프로필"""
    return UserProfile(
        goal="다이어트",
        weight=70.0,
        height=170.0,
        age=30,
        gender="male",
        activity_level="moderate",
        restrictions=["돼지고기"],
        health_conditions=[],
        skill_level="중급",
        cooking_time="30분",
        budget=50000,
        budget_type="weekly",
        meals_per_day=3,
        days=2,  # 2일 테스트
        calorie_adjustment=None,
    )


@pytest.mark.asyncio
async def test_single_meal_planning(sample_profile):
    """단일 끼니 계획 테스트"""
    # 1일 1끼로 제한
    sample_profile.days = 1
    sample_profile.meals_per_day = 1

    # 초기 상태 생성
    initial_state: MealPlanState = {
        "profile": sample_profile,
        "daily_targets": None,
        "per_meal_targets": None,
        "per_meal_budget": 0,
        "current_day": 0,
        "current_meal_index": 0,
        "current_meal_type": "점심",
        "nutritionist_recommendation": None,
        "chef_recommendation": None,
        "budget_recommendation": None,
        "current_menu": None,
        "validation_results": [],
        "retry_count": 0,
        "completed_meals": [],
        "weekly_plan": [],
        "events": [],
    }

    # 그래프 가져오기
    graph = get_meal_planner_graph()

    # 그래프 실행
    final_state = await graph.ainvoke(initial_state)

    # 결과 검증
    assert final_state is not None
    assert len(final_state["weekly_plan"]) == 1
    assert len(final_state["weekly_plan"][0].meals) == 1

    logger.info("single_meal_test_completed", final_state=final_state)


@pytest.mark.asyncio
async def test_full_week_planning(sample_profile):
    """전체 주간 계획 테스트 (2일 3끼)"""
    # 초기 상태 생성
    initial_state: MealPlanState = {
        "profile": sample_profile,
        "daily_targets": None,
        "per_meal_targets": None,
        "per_meal_budget": 0,
        "current_day": 0,
        "current_meal_index": 0,
        "current_meal_type": "아침",
        "nutritionist_recommendation": None,
        "chef_recommendation": None,
        "budget_recommendation": None,
        "current_menu": None,
        "validation_results": [],
        "retry_count": 0,
        "completed_meals": [],
        "weekly_plan": [],
        "events": [],
    }

    # 그래프 가져오기
    graph = get_meal_planner_graph()

    # 그래프 실행
    final_state = await graph.ainvoke(initial_state)

    # 결과 검증
    assert final_state is not None
    assert len(final_state["weekly_plan"]) == 2  # 2일
    assert all(len(day.meals) == 3 for day in final_state["weekly_plan"])  # 각 날마다 3끼

    # 각 날짜의 영양소 합계 확인
    for day_plan in final_state["weekly_plan"]:
        assert day_plan.total_calories > 0
        assert day_plan.total_cost > 0
        logger.info(
            "day_plan_summary",
            day=day_plan.day,
            total_calories=day_plan.total_calories,
            total_cost=day_plan.total_cost,
            meals=[m.menu_name for m in day_plan.meals],
        )


@pytest.mark.asyncio
async def test_streaming_execution(sample_profile):
    """스트리밍 실행 테스트 (SSE 준비)"""
    # 1일 1끼로 제한
    sample_profile.days = 1
    sample_profile.meals_per_day = 1

    initial_state: MealPlanState = {
        "profile": sample_profile,
        "daily_targets": None,
        "per_meal_targets": None,
        "per_meal_budget": 0,
        "current_day": 0,
        "current_meal_index": 0,
        "current_meal_type": "점심",
        "nutritionist_recommendation": None,
        "chef_recommendation": None,
        "budget_recommendation": None,
        "current_menu": None,
        "validation_results": [],
        "retry_count": 0,
        "completed_meals": [],
        "weekly_plan": [],
        "events": [],
    }

    graph = get_meal_planner_graph()

    # 스트리밍 실행
    event_count = 0
    async for chunk in graph.astream(initial_state):
        event_count += 1
        logger.info("stream_chunk", chunk_number=event_count, chunk=chunk)

    assert event_count > 0
    logger.info("streaming_test_completed", total_events=event_count)


@pytest.mark.asyncio
async def test_health_condition_planning(sample_profile):
    """건강 조건이 있는 사용자 테스트"""
    # 당뇨 + 고혈압
    sample_profile.health_conditions = ["당뇨", "고혈압"]
    sample_profile.days = 1
    sample_profile.meals_per_day = 2

    initial_state: MealPlanState = {
        "profile": sample_profile,
        "daily_targets": None,
        "per_meal_targets": None,
        "per_meal_budget": 0,
        "current_day": 0,
        "current_meal_index": 0,
        "current_meal_type": "아침",
        "nutritionist_recommendation": None,
        "chef_recommendation": None,
        "budget_recommendation": None,
        "current_menu": None,
        "validation_results": [],
        "retry_count": 0,
        "completed_meals": [],
        "weekly_plan": [],
        "events": [],
    }

    graph = get_meal_planner_graph()
    final_state = await graph.ainvoke(initial_state)

    assert final_state is not None
    assert len(final_state["weekly_plan"]) == 1
    assert len(final_state["weekly_plan"][0].meals) == 2

    # 영양소 제한 준수 확인 (간접적 검증)
    for meal in final_state["weekly_plan"][0].meals:
        # 당뇨: 저당류, 고혈압: 저나트륨 (Mock 모드에서는 대략적 확인)
        assert meal.sodium_mg < 1000  # 나트륨 제한
        assert meal.sugar_g < 50  # 당류 제한

    logger.info("health_condition_test_completed", final_state=final_state)
