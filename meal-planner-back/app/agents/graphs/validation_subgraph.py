"""Validation Subgraph"""
from langgraph.graph import StateGraph, START, END
from app.models.state import MealPlanState
from app.agents.nodes.validation_supervisor import validation_supervisor
from app.agents.nodes.validation.nutrition_checker import nutrition_checker
from app.agents.nodes.validation.allergy_checker import allergy_checker
from app.agents.nodes.validation.time_checker import time_checker
from app.agents.nodes.validation.health_checker import health_checker
from app.agents.nodes.validation.budget_checker import budget_checker
from app.agents.nodes.validation_aggregator import validation_aggregator


def create_validation_subgraph() -> StateGraph:
    """Validation Subgraph 생성

    구조:
    START → validation_supervisor (Send API)
          ├→ nutrition_checker ──┐
          ├→ allergy_checker ────┤
          ├→ time_checker ───────┤
          ├→ health_checker ─────┤
          └→ budget_checker ─────┴→ validation_aggregator → END

    Returns:
        StateGraph 인스턴스
    """
    # Subgraph 생성
    subgraph = StateGraph(MealPlanState)

    # 노드 추가
    subgraph.add_node("validation_supervisor", validation_supervisor)
    subgraph.add_node("nutrition_checker", nutrition_checker)
    subgraph.add_node("allergy_checker", allergy_checker)
    subgraph.add_node("time_checker", time_checker)
    subgraph.add_node("health_checker", health_checker)
    subgraph.add_node("budget_checker", budget_checker)
    subgraph.add_node("validation_aggregator", validation_aggregator)

    # 엣지 추가
    # Supervisor는 Send API를 사용하므로 자동으로 5개 검증기로 분기됨
    subgraph.add_edge(START, "validation_supervisor")

    # 5개 검증기 완료 후 aggregator로 수렴
    subgraph.add_edge("nutrition_checker", "validation_aggregator")
    subgraph.add_edge("allergy_checker", "validation_aggregator")
    subgraph.add_edge("time_checker", "validation_aggregator")
    subgraph.add_edge("health_checker", "validation_aggregator")
    subgraph.add_edge("budget_checker", "validation_aggregator")

    # aggregator 완료 후 종료
    subgraph.add_edge("validation_aggregator", END)

    return subgraph
