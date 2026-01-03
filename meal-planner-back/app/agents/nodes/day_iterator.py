"""Day Iterator Node"""
from typing import Literal
from app.models.state import MealPlanState, DailyPlan
from app.utils.constants import MEAL_TYPES
from app.utils.nutrition import calculate_daily_totals
from app.utils.logging import get_logger

logger = get_logger(__name__)


def day_iterator(state: MealPlanState) -> dict | Literal["__end__"]:
    """끼니/날짜 진행 관리 노드

    현재 메뉴를 저장하고 다음 끼니 또는 다음 날로 진행합니다:
    1. 현재 메뉴를 completed_meals에 추가
    2. 하루의 모든 끼니 완료 확인
       - 완료 시: daily_plan을 weekly_plan에 저장하고 다음 날로
       - 미완료: 다음 끼니로 진행
    3. 전체 주간 계획 완료 시 종료

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict 또는 "__end__" (종료 신호)
    """
    profile = state["profile"]

    # CRITICAL: Validate meals_per_day BEFORE any processing
    meals_per_day = profile.meals_per_day
    if meals_per_day < 1 or meals_per_day > len(MEAL_TYPES):
        logger.error(
            "day_iterator_invalid_meals_per_day",
            meals_per_day=meals_per_day,
            max_allowed=len(MEAL_TYPES)
        )
        # Early termination with error
        return {
            "error_message": f"Invalid meals_per_day: {meals_per_day}. Must be 1-{len(MEAL_TYPES)}",
            "events": [{
                "type": "error",
                "node": "day_iterator",
                "status": "invalid_config",
                "data": {"meals_per_day": meals_per_day}
            }]
        }

    current_menu = state["current_menu"]
    completed_meals = state["completed_meals"].copy()
    weekly_plan = state["weekly_plan"].copy()

    # 1. 검증 경고가 있으면 current_menu에 추가
    validation_warnings = state.get("_validation_warnings", [])
    if validation_warnings:
        # Menu는 Pydantic 모델이므로 copy 후 수정
        current_menu = current_menu.model_copy(update={"validation_warnings": validation_warnings})
        logger.warning(
            "day_iterator_validation_warnings_attached",
            menu=current_menu.menu_name,
            warnings=validation_warnings,
        )

    # 2. 현재 메뉴를 completed_meals에 추가
    completed_meals.append(current_menu)

    logger.info(
        "day_iterator_menu_saved",
        day=state["current_day"],
        meal_type=state["current_meal_type"],
        menu=current_menu.menu_name,
        completed_count=len(completed_meals),
    )

    # 2. 하루 끼니 완료 확인
    meals_per_day = profile.meals_per_day
    current_meal_index = state["current_meal_index"]
    next_meal_index = current_meal_index + 1

    if next_meal_index >= meals_per_day:
        # 하루 완료: DailyPlan 생성 후 weekly_plan에 추가
        daily_totals = calculate_daily_totals(completed_meals)

        daily_plan = DailyPlan(
            day=state["current_day"],
            meals=completed_meals,
            total_calories=daily_totals["total_calories"],
            total_carb_g=daily_totals["total_carb_g"],
            total_protein_g=daily_totals["total_protein_g"],
            total_fat_g=daily_totals["total_fat_g"],
            total_cost=daily_totals["total_cost"],
        )

        weekly_plan.append(daily_plan)

        logger.info(
            "day_iterator_day_completed",
            day=state["current_day"],
            total_calories=daily_totals["total_calories"],
            total_cost=daily_totals["total_cost"],
        )

        # 3. 다음 날 계산 및 전체 주간 계획 완료 확인
        next_day = state["current_day"] + 1

        if next_day > profile.days:
            # 전체 완료: 종료
            logger.info(
                "day_iterator_plan_completed",
                total_days=profile.days,
                total_menus=len(completed_meals) + sum(len(d.meals) for d in weekly_plan) - len(completed_meals),
            )

            return {
                "weekly_plan": weekly_plan,
                "completed_meals": [],  # 초기화
                "events": [{
                    "type": "complete",
                    "node": "day_iterator",
                    "status": "completed",
                    "data": {"total_days": profile.days}
                }],
            }

        # 다음 날로 진행
        next_meal_type = MEAL_TYPES[0]

        logger.info(
            "day_iterator_next_day",
            current_day=state["current_day"],
            next_day=next_day,
        )

        return {
            "weekly_plan": weekly_plan,
            "completed_meals": [],  # 새로운 날 시작
            "current_day": next_day,
            "current_meal_index": 0,
            "current_meal_type": next_meal_type,
            "retry_count": 0,  # 재시도 카운터 초기화
            "validation_results": [],  # 검증 결과 초기화
            "_validation_warnings": None,  # 검증 경고 초기화
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "current_menu": None,
            "events": [{
                "type": "progress",
                "node": "day_iterator",
                "status": "next_day",
                "data": {
                    "day": next_day,
                    "meal": 1,  # 새로운 날의 첫 끼니
                    "meal_type": next_meal_type,
                }
            }],
        }
    else:
        # 같은 날 다음 끼니로 진행
        # CRITICAL: Validate next_meal_index before accessing MEAL_TYPES
        if next_meal_index >= len(MEAL_TYPES):
            logger.error(
                "day_iterator_meal_index_overflow",
                next_meal_index=next_meal_index,
                max_index=len(MEAL_TYPES) - 1,
                meals_per_day=meals_per_day
            )
            # Fallback: Use last available meal type
            next_meal_type = MEAL_TYPES[-1]
            logger.warning(
                "day_iterator_using_fallback_meal_type",
                fallback=next_meal_type
            )
        else:
            next_meal_type = MEAL_TYPES[next_meal_index]

        logger.info(
            "day_iterator_next_meal",
            day=state["current_day"],
            current_meal=state["current_meal_type"],
            next_meal=next_meal_type,
        )

        return {
            "completed_meals": completed_meals,
            "current_day": state["current_day"],  # CRITICAL: Include current_day for state continuity
            "current_meal_index": next_meal_index,
            "current_meal_type": next_meal_type,
            "retry_count": 0,  # 재시도 카운터 초기화
            "validation_results": [],  # 검증 결과 초기화
            "_validation_warnings": None,  # 검증 경고 초기화
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "current_menu": None,
            "events": [{
                "type": "progress",
                "node": "day_iterator",
                "status": "next_meal",
                "data": {
                    "day": state["current_day"],
                    "meal": next_meal_index + 1,  # 1-indexed for display
                    "meal_type": next_meal_type,
                }
            }],
        }
