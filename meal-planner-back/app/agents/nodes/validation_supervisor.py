"""Validation Supervisor Node (Send API)"""
from langgraph.types import Send, Command
from app.models.state import MealPlanState
from app.utils.logging import get_logger

logger = get_logger(__name__)


def validation_supervisor(state: MealPlanState) -> Command:
    """5개의 검증기에게 병렬로 작업 분배

    Command API를 사용하여 nutrition_checker, allergy_checker, time_checker,
    health_checker, budget_checker에 동시 작업 전송

    Args:
        state: 현재 그래프 상태

    Returns:
        Command 객체 (병렬 실행)
    """
    logger.info(
        "validation_supervisor_started",
        menu=state["current_menu"].menu_name if state["current_menu"] else None,
        day=state["current_day"],
        meal_type=state["current_meal_type"],
    )

    # 5개의 검증기에 동시에 작업 분배
    return Command(
        goto=[
            Send("nutrition_checker", state),
            Send("allergy_checker", state),
            Send("time_checker", state),
            Send("health_checker", state),
            Send("budget_checker", state),
        ]
    )
