"""Meal Planning Supervisor Node (Send API)"""
from langgraph.types import Send, Command
from app.models.state import MealPlanState
from app.utils.logging import get_logger

logger = get_logger(__name__)


def meal_planning_supervisor(state: MealPlanState) -> Command:
    """3명의 전문가에게 병렬로 작업 분배

    Command API를 사용하여 nutritionist, chef, budget 노드에 동시 작업 전송
    budget은 chef의 ingredients를 참조하여 Tavily 가격 검색 수행

    Args:
        state: 현재 그래프 상태

    Returns:
        Command 객체 (병렬 실행)
    """
    logger.info(
        "meal_planning_supervisor_started",
        meal_type=state["current_meal_type"],
        day=state["current_day"],
    )

    # nutritionist, chef, budget에게 동시에 작업 분배
    # budget은 chef_recommendation이 있으면 Tavily 가격 검색, 없으면 LLM만 사용
    return Command(
        goto=[
            Send("nutritionist", state),
            Send("chef", state),
            Send("budget", state),
        ]
    )
