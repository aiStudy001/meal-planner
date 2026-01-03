"""Budget Router - chef 완료 후 budget 실행"""
from langgraph.types import Send, Command

from app.models.state import MealPlanState
from app.utils.logging import get_logger

logger = get_logger(__name__)


def budget_router(state: MealPlanState) -> Command:
    """Chef 결과를 받아 Budget 실행

    역할:
    - chef가 생성한 ingredients를 확인
    - budget 노드로 전달

    Args:
        state: chef가 업데이트한 상태

    Returns:
        Command 객체 with Send to budget node
    """
    logger.info(
        "budget_router_triggered",
        has_ingredients=bool(state.get("current_menu", {}).get("ingredients"))
    )

    # Budget 노드로 전달
    return Command(goto=[Send("budget", state)])
