"""조리 시간 검증 노드"""
from app.models.state import MealPlanState, ValidationResult
from app.utils.constants import COOKING_TIME_LIMITS
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def time_checker(state: MealPlanState) -> dict:
    """조리 시간 제한 검증

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    menu = state["current_menu"]
    profile = state["profile"]
    time_limit = COOKING_TIME_LIMITS[profile.cooking_time]

    logger.info(
        "time_checker_started",
        menu=menu.menu_name,
        cooking_time=menu.cooking_time_minutes,
        time_limit=time_limit,
    )

    issues = []

    if menu.cooking_time_minutes > time_limit:
        issues.append(
            f"조리 시간 초과: 제한 {time_limit}분, "
            f"실제 {menu.cooking_time_minutes}분 "
            f"(초과: {menu.cooking_time_minutes - time_limit}분)"
        )
        logger.warning(
            "time_limit_exceeded",
            cooking_time=menu.cooking_time_minutes,
            time_limit=time_limit,
            excess=menu.cooking_time_minutes - time_limit,
        )

    passed = len(issues) == 0

    result = ValidationResult(
        validator="time_checker",
        passed=passed,
        issues=issues,
    )

    logger.info(
        "time_checker_completed",
        passed=passed,
        issue_count=len(issues),
    )

    return {
        "validation_results": [result],
        "events": [{
            "type": "validation",
            "node": "time_checker",
            "status": "completed",
            "data": {
                "passed": passed,
                "issues": issues,
            }
        }],
    }
