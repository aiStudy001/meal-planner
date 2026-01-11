"""Meal Planning Subgraph"""
from langgraph.graph import StateGraph, START, END
from app.models.state import MealPlanState
from app.agents.nodes.meal_planning_supervisor import meal_planning_supervisor
from app.agents.nodes.meal_planning.nutritionist import nutritionist_agent
from app.agents.nodes.meal_planning.chef import chef_agent
from app.agents.nodes.meal_planning.budget import budget_agent
from app.agents.nodes.meal_planning.budget_router import budget_router
from app.agents.nodes.meal_planning.conflict_resolver import conflict_resolver


def create_meal_planning_subgraph() -> StateGraph:
    """Meal Planning Subgraph 생성

    구조:
    START → meal_planning_supervisor (Send API)
          ├→ nutritionist ──┐
          ├→ chef ──────────┤
          └→ budget ─────────┴→ conflict_resolver → END

    budget은 chef_recommendation의 ingredients를 참조하여 Tavily 가격 검색 수행

    Returns:
        StateGraph 인스턴스
    """
    # Subgraph 생성
    subgraph = StateGraph(MealPlanState)

    # 노드 추가
    subgraph.add_node("meal_planning_supervisor", meal_planning_supervisor)
    subgraph.add_node("nutritionist", nutritionist_agent)
    subgraph.add_node("chef", chef_agent)
    subgraph.add_node("budget_router", budget_router)
    subgraph.add_node("budget", budget_agent)
    subgraph.add_node("conflict_resolver", conflict_resolver)

    # 엣지 추가
    # Supervisor는 Send API를 사용하여 nutritionist, chef, budget에 병렬 분기
    subgraph.add_edge(START, "meal_planning_supervisor")

    # 모든 전문가가 conflict_resolver로 수렴
    subgraph.add_edge("nutritionist", "conflict_resolver")
    subgraph.add_edge("chef", "conflict_resolver")
    subgraph.add_edge("budget", "conflict_resolver")

    # conflict_resolver 완료 후 종료
    subgraph.add_edge("conflict_resolver", END)

    return subgraph


# 싱글톤 인스턴스
_subgraph_instance = None


def get_meal_planning_subgraph():
    """Meal Planning Subgraph 싱글톤 인스턴스 반환"""
    global _subgraph_instance
    if _subgraph_instance is None:
        _subgraph_instance = create_meal_planning_subgraph().compile()
    return _subgraph_instance
