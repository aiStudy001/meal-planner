"""Validation Aggregator Node"""
from app.models.state import MealPlanState
from app.utils.logging import get_logger

logger = get_logger(__name__)


def calculate_total_completed_meals(state: MealPlanState) -> int:
    """전체 완료된 끼니 수 계산 (weekly_plan + completed_meals)

    Args:
        state: 현재 그래프 상태

    Returns:
        총 완료된 끼니 수
    """
    # weekly_plan: 이미 완료된 날짜들 (각 날은 DailyPlan 객체)
    weekly_plan = state.get("weekly_plan", [])
    total_from_weekly_plan = sum(len(day.meals) for day in weekly_plan)

    # completed_meals: 현재 진행 중인 날의 완료된 끼니들
    current_day_completed = len(state.get("completed_meals", []))

    return total_from_weekly_plan + current_day_completed


async def validation_aggregator(state: MealPlanState) -> dict:
    """검증 결과 집계 노드

    3개의 검증기(nutrition_checker, allergy_checker, time_checker)가
    병렬 실행된 후 결과를 집계합니다.

    State의 validation_results는 이미 reducer로 자동 집계되므로
    이 노드는 로깅과 이벤트 발행만 수행합니다.

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    validation_results = state["validation_results"]

    # 검증 결과 분석
    total_validators = len(validation_results)
    passed_validators = [v for v in validation_results if v.passed]
    failed_validators = [v for v in validation_results if not v.passed]

    all_passed = len(failed_validators) == 0

    logger.info(
        "validation_aggregator_completed",
        total_validators=total_validators,
        passed_count=len(passed_validators),
        failed_count=len(failed_validators),
        all_passed=all_passed,
        failed_validators=[v.validator for v in failed_validators],
    )

    # 각 실패한 검증기의 이슈 로깅
    for validator in failed_validators:
        issues = validator.details.get("issues", []) if validator.details else []
        logger.warning(
            "validation_failed",
            validator=validator.validator,
            issues=issues,
            reason=validator.reason,
        )

    # 실패한 검증 정보를 previous_validation_failures에 저장
    failed_validations = [
        {
            "validator": result.validator,
            "issues": result.issues,
            "retry_count": state.get("retry_count", 0),
            "menu_name": state["current_menu"].menu_name if state.get("current_menu") else "Unknown",
        }
        for result in failed_validators
    ]

    current_menu = state.get("current_menu")

    # Calculate progress: include current meal if validation passed
    total_completed = calculate_total_completed_meals(state)
    if all_passed:
        total_completed += 1  # Include current meal in count

    return {
        "previous_validation_failures": failed_validations,
        "events": [{
            "type": "meal_complete" if all_passed else "progress",
            "node": "validation_aggregator",
            "status": "completed",
            "data": {
                "all_passed": all_passed,
                "passed_count": len(passed_validators),
                "failed_count": len(failed_validators),
                "failed_validators": [v.validator for v in failed_validators],
                # Add context data for meal tracking
                "day": state.get("current_day"),
                "meal": state.get("current_meal_index") + 1,  # Convert 0-indexed to 1-indexed for display
                "meal_type": state.get("current_meal_type"),
                "menu": current_menu.menu_name if current_menu else None,
                "calories": current_menu.calories if current_menu else 0,
                "cost": current_menu.estimated_cost if current_menu else 0,
                # Add progress tracking (cumulative calculation)
                "completed_meals": total_completed,
                "total_meals": state.get("profile").days * state.get("profile").meals_per_day,
            }
        }],
    }
