"""Main Meal Planner Graph"""
from langgraph.graph import StateGraph, START, END
from app.models.state import MealPlanState
from app.agents.nodes.nutrition_calculator import nutrition_calculator
from app.agents.nodes.decision_maker import decision_maker
from app.agents.nodes.retry_router import retry_router
from app.agents.nodes.day_iterator import day_iterator
from app.agents.nodes.meal_planning_supervisor import meal_planning_supervisor
from app.agents.nodes.meal_planning.nutritionist import nutritionist_agent
from app.agents.nodes.meal_planning.chef import chef_agent
from app.agents.nodes.meal_planning.budget import budget_agent
from app.agents.nodes.meal_planning.conflict_resolver import conflict_resolver
from app.agents.nodes.validation_supervisor import validation_supervisor
from app.agents.nodes.validation.nutrition_checker import nutrition_checker
from app.agents.nodes.validation.allergy_checker import allergy_checker
from app.agents.nodes.validation.time_checker import time_checker
from app.agents.nodes.validation.health_checker import health_checker
from app.agents.nodes.validation.budget_checker import budget_checker
from app.agents.nodes.validation_aggregator import validation_aggregator


def create_main_graph() -> StateGraph:
    """메인 식단 계획 그래프 생성

    전체 구조:
    START → nutrition_calculator
          → meal_planning_supervisor (Send API)
            ├→ nutritionist ──┐
            ├→ chef ──────────┤
            └→ budget ────────┴→ conflict_resolver
          → validation_supervisor (Send API)
            ├→ nutrition_checker ──┐
            ├→ allergy_checker ────┤
            ├→ time_checker ───────┤
            ├→ health_checker ─────┤
            └→ budget_checker ─────┴→ validation_aggregator
          → 조건부 분기 (decision_maker 함수)
            ├→ day_iterator → (meal_planning_supervisor or END)
            └→ retry_router → meal_planning_supervisor (3명 전문가 재실행)

    Returns:
        컴파일된 StateGraph 인스턴스
    """
    # 메인 그래프 생성
    graph = StateGraph(MealPlanState)

    # === 노드 추가 ===

    # 초기 계산
    graph.add_node("nutrition_calculator", nutrition_calculator)

    # Meal Planning 노드들
    graph.add_node("meal_planning_supervisor", meal_planning_supervisor)
    graph.add_node("nutritionist", nutritionist_agent)
    graph.add_node("chef", chef_agent)
    graph.add_node("budget", budget_agent)
    graph.add_node("conflict_resolver", conflict_resolver)

    # Validation 노드들
    graph.add_node("validation_supervisor", validation_supervisor)
    graph.add_node("nutrition_checker", nutrition_checker)
    graph.add_node("allergy_checker", allergy_checker)
    graph.add_node("time_checker", time_checker)
    graph.add_node("health_checker", health_checker)
    graph.add_node("budget_checker", budget_checker)
    graph.add_node("validation_aggregator", validation_aggregator)

    # 라우팅 및 반복 노드들
    # decision_maker는 조건부 라우팅 함수이므로 노드로 추가하지 않음
    graph.add_node("retry_router", retry_router)
    graph.add_node("day_iterator", day_iterator)

    # === 엣지 추가 ===

    # 1. 시작: nutrition_calculator
    graph.add_edge(START, "nutrition_calculator")

    # 2. nutrition_calculator → meal_planning_supervisor
    graph.add_edge("nutrition_calculator", "meal_planning_supervisor")

    # 3. Meal Planning Subgraph (Send API 자동 분기)
    # meal_planning_supervisor는 Send를 사용하여 자동으로 nutritionist, chef, budget로 분기
    graph.add_edge("nutritionist", "conflict_resolver")
    graph.add_edge("chef", "conflict_resolver")
    graph.add_edge("budget", "conflict_resolver")

    # 4. conflict_resolver → validation_supervisor
    graph.add_edge("conflict_resolver", "validation_supervisor")

    # 5. Validation Subgraph (Send API 자동 분기)
    # validation_supervisor는 Send를 사용하여 자동으로 5개 검증기로 분기
    graph.add_edge("nutrition_checker", "validation_aggregator")
    graph.add_edge("allergy_checker", "validation_aggregator")
    graph.add_edge("time_checker", "validation_aggregator")
    graph.add_edge("health_checker", "validation_aggregator")
    graph.add_edge("budget_checker", "validation_aggregator")

    # 6. validation_aggregator → 조건부 라우팅 (decision_maker 함수 사용)
    # 모든 검증 통과 → day_iterator
    # 일부 검증 실패 → retry_router
    graph.add_conditional_edges(
        "validation_aggregator",
        decision_maker,  # 라우팅 함수
        {
            "day_iterator": "day_iterator",
            "retry_router": "retry_router",
        }
    )

    # 7. retry_router는 Command API를 사용하여 meal_planning_supervisor로 자동 이동
    # (3명 전문가 모두 재실행)

    # 8. day_iterator → 조건부 라우팅
    # 다음 끼니/날짜 → meal_planning_supervisor
    # 전체 완료 → END
    def should_continue(state: MealPlanState) -> str:
        """day_iterator 후 계속 여부 판단"""
        # weekly_plan 길이가 목표 일수와 같으면 완료
        profile = state["profile"]
        weekly_plan = state["weekly_plan"]
        if len(weekly_plan) >= profile.days:
            return END
        return "meal_planning_supervisor"

    graph.add_conditional_edges(
        "day_iterator",
        should_continue,
        {
            "meal_planning_supervisor": "meal_planning_supervisor",
            END: END,
        }
    )

    # 그래프 컴파일
    compiled_graph = graph.compile()

    return compiled_graph


# 편의 함수: 그래프 인스턴스 가져오기
_graph_instance = None

def get_meal_planner_graph():
    """메인 그래프 싱글톤 인스턴스 반환"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_main_graph()
    return _graph_instance
