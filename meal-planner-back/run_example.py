"""식단 계획 그래프 실행 예제

Mock 모드로 LLM API 호출 없이 전체 시스템을 테스트합니다.
"""
import asyncio
import os
from dotenv import load_dotenv
from app.models.state import UserProfile, MealPlanState
from app.agents.graphs.main_graph import get_meal_planner_graph
from app.utils.logging import setup_logging, get_logger

# 환경 변수 로드
load_dotenv()

# 로깅 설정
setup_logging("INFO")
logger = get_logger(__name__)


async def main():
    """메인 실행 함수"""
    logger.info("meal_planner_started")

    # 1. 사용자 프로필 생성
    profile = UserProfile(
        goal="다이어트",
        weight=70.0,
        height=170.0,
        age=30,
        gender="male",
        activity_level="moderate",
        restrictions=["돼지고기", "갑각류"],
        health_conditions=["당뇨"],
        skill_level="중급",
        cooking_time="30분 이내",
        budget=50000,
        budget_type="weekly",
        meals_per_day=3,
        days=2,  # 2일 계획
        calorie_adjustment=None,
    )

    logger.info("user_profile_created", profile=profile.model_dump())

    # 2. 초기 상태 생성
    initial_state: MealPlanState = {
        "profile": profile,
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
        "max_retries": 5,  # 최대 재시도 횟수
        "error_message": None,
        "completed_meals": [],
        "weekly_plan": [],
        "events": [],
    }

    # 3. 그래프 가져오기
    graph = get_meal_planner_graph()
    logger.info("graph_initialized")

    # 4. 그래프 실행 (스트리밍 모드)
    print("\n" + "="*80)
    print(f"식단 계획 시작 ({profile.days}일, {profile.meals_per_day}끼)")
    print("="*80 + "\n")

    # Recursion limit 동적 계산
    # 각 끼니당 약 11개 노드 (supervisor, experts, validators, aggregator, iterator 등)
    # 초기 노드 (nutrition_calculator) 1개 + 여유 20%
    total_meals = profile.days * profile.meals_per_day
    estimated_nodes = 1 + (total_meals * 11)
    recursion_limit = int(estimated_nodes * 1.2)  # 20% 여유

    config = {"recursion_limit": recursion_limit}
    logger.info("recursion_limit_calculated",
                days=profile.days,
                meals_per_day=profile.meals_per_day,
                total_meals=total_meals,
                recursion_limit=recursion_limit)

    event_count = 0
    async for chunk in graph.astream(initial_state, config=config):
        event_count += 1

        # 청크에서 노드 이름과 상태 추출
        for node_name, node_state in chunk.items():
            if isinstance(node_state, dict) and "events" in node_state:
                for event in node_state["events"]:
                    event_type = event.get("type")
                    node = event.get("node")
                    status = event.get("status")
                    data = event.get("data", {})

                    print(f"[{event_type.upper()}] {node} - {status}")
                    if data:
                        for key, value in data.items():
                            print(f"  {key}: {value}")
                    print()

        # 진행 상황 로깅
        logger.info("stream_event", event_number=event_count, chunk_keys=list(chunk.keys()))

    # 5. 최종 상태 가져오기
    final_state = await graph.ainvoke(initial_state, config=config)

    # 6. 결과 출력
    print("\n" + "="*80)
    print("주간 식단 계획 완료")
    print("="*80 + "\n")

    for day_plan in final_state["weekly_plan"]:
        print(f"\n📅 {day_plan.day}일차")
        print(f"   총 칼로리: {day_plan.total_calories:.0f}kcal")
        print(f"   총 비용: {day_plan.total_cost:,}원")
        print(f"   영양소: 탄수화물 {day_plan.total_carb_g:.1f}g | "
              f"단백질 {day_plan.total_protein_g:.1f}g | "
              f"지방 {day_plan.total_fat_g:.1f}g")
        print("\n   메뉴:")

        for meal in day_plan.meals:
            # 검증 경고가 있으면 ⚠️ 표시
            warning_prefix = "⚠️  " if meal.validation_warnings else ""
            print(f"\n   {warning_prefix}🍽️  {meal.meal_type}: {meal.menu_name}")
            print(f"      칼로리: {meal.calories}kcal")
            print(f"      비용: {meal.estimated_cost:,}원")
            print(f"      조리시간: {meal.cooking_time_minutes}분")
            print(f"      재료: {', '.join([f'{i["name"]} {i["amount"]}' for i in meal.ingredients[:3]])}...")

            # 검증 경고 내용 출력
            if meal.validation_warnings:
                print(f"\n      ⚠️ 검증 경고:")
                for warning in meal.validation_warnings:
                    print(f"         - {warning}")

    print("\n" + "="*80)
    logger.info("meal_planner_completed", total_days=len(final_state["weekly_plan"]))


if __name__ == "__main__":
    # MOCK_MODE=true로 설정되어 있는지 확인
    if os.getenv("MOCK_MODE", "false").lower() != "true":
        print("[WARNING] MOCK_MODE is not enabled.")
        print("Set MOCK_MODE=true in .env file\n")

    asyncio.run(main())
