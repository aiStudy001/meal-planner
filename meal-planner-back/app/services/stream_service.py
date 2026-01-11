"""
SSE 스트리밍 서비스

Event-Driven 방식으로 LangGraph 이벤트를 SSE 형식으로 변환
기존 노드를 수정하지 않고 이벤트를 읽기만 함
"""

import asyncio
import json
from typing import AsyncGenerator
from app.agents.graphs.main_graph import get_meal_planner_graph
from app.models.state import MealPlanState, UserProfile
from app.models.requests import MealPlanRequest
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def stream_meal_plan(
    request: MealPlanRequest
) -> AsyncGenerator[str, None]:
    """
    식단 계획을 SSE로 스트리밍

    Args:
        request: 식단 계획 요청

    Yields:
        SSE 형식 문자열 ("data: {json}\n\n")
    """
    try:
        # 1. Request → UserProfile 변환
        profile = UserProfile(
            goal=request.goal,
            weight=request.weight,
            height=request.height,
            age=request.age,
            gender=request.gender,
            activity_level=request.activity_level,
            restrictions=request.restrictions,
            health_conditions=request.health_conditions,
            calorie_adjustment=request.calorie_adjustment,
            macro_ratio=request.macro_ratio,
            budget=request.budget,
            budget_type=request.budget_type,
            budget_distribution=request.budget_distribution,
            cooking_time=request.cooking_time,
            skill_level=request.skill_level,
            meals_per_day=request.meals_per_day,
            days=request.days,
        )

        logger.info("stream_started", profile=profile.model_dump())

        # 2. 초기 상태 생성 (run_example.py 참고)
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
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # 3. Recursion limit 동적 계산
        total_meals = profile.days * profile.meals_per_day
        estimated_nodes = 1 + (total_meals * 11)  # 각 끼니당 약 11개 노드
        recursion_limit = int(estimated_nodes * 1.2)  # 20% 여유
        config = {"recursion_limit": recursion_limit}

        logger.info(
            "recursion_limit_calculated",
            days=profile.days,
            meals_per_day=profile.meals_per_day,
            total_meals=total_meals,
            recursion_limit=recursion_limit,
        )

        # 4. Graph 가져오기
        graph = get_meal_planner_graph()

        # 5. 그래프 실행 - 이벤트 스트리밍
        event_count = 0
        partial_events_sent = 0
        final_state = None  # Store final state from astream

        async for chunk in graph.astream(initial_state, config=config):
            event_count += 1

            # Save the last chunk as final state
            final_state = chunk

            # EC-022: Per-chunk error handling for mid-stream resilience
            try:
                # Chunk에서 events 추출
                for node_name, node_state in chunk.items():
                    if isinstance(node_state, dict) and "events" in node_state:
                        for event in node_state["events"]:
                            # Node 이벤트 → SSE 이벤트 변환
                            sse_event = transform_event(event, node_name)
                            yield format_sse(sse_event)
                            partial_events_sent += 1

                logger.debug(
                    "stream_event",
                    event_number=event_count,
                    chunk_keys=list(chunk.keys()),
                )

            except Exception as chunk_error:
                # EC-022: Log chunk error but continue streaming
                logger.warning(
                    "stream_chunk_error",
                    event_number=event_count,
                    error=str(chunk_error),
                    partial_events_sent=partial_events_sent,
                )
                # Send partial error event to client
                error_event = {
                    "type": "warning",
                    "data": {
                        "message": f"일부 이벤트 처리 중 오류 발생 (chunk {event_count})",
                        "code": "CHUNK_ERROR",
                        "partial_success": True,
                    },
                }
                yield format_sse(error_event)
                # Continue processing remaining chunks

        # 6. Extract weekly_plan from final state
        # The final_state from astream contains the complete state
        weekly_plan = []
        if final_state:
            # Find the node that contains weekly_plan
            for node_name, node_state in final_state.items():
                if isinstance(node_state, dict) and "weekly_plan" in node_state:
                    weekly_plan = node_state["weekly_plan"]
                    break

        # 7. 완료 이벤트 전송
        completion_event = {
            "type": "complete",
            "data": {"meal_plan": serialize_weekly_plan(weekly_plan)},
        }
        yield format_sse(completion_event)

        logger.info(
            "stream_completed",
            total_days=len(weekly_plan),
            total_events=event_count,
            partial_events_sent=partial_events_sent,
        )

    except asyncio.CancelledError:
        # EC-021: Client disconnect - log and re-raise for FastAPI cleanup
        logger.warning(
            "stream_client_disconnected",
            event_count=event_count if 'event_count' in locals() else 0,
            partial_events_sent=partial_events_sent if 'partial_events_sent' in locals() else 0,
        )
        raise  # Re-raise for FastAPI to handle cleanup

    except Exception as e:
        logger.error("stream_error", error=str(e), exc_info=True)

        # 에러 이벤트 전송
        error_event = {
            "type": "error",
            "data": {"message": str(e), "code": "GRAPH_ERROR"},
        }
        yield format_sse(error_event)


def transform_event(event: dict, node_name: str) -> dict:
    """
    Node 이벤트를 SSE 이벤트로 변환

    Node events → SSE events:
    - validation nodes → "validation" type
    - validation_aggregator (all_passed) → "meal_complete" type
    - retry_router → "retry" type
    - others → "progress" type

    Args:
        event: 노드 이벤트
        node_name: 노드 이름

    Returns:
        SSE 이벤트 딕셔너리
    """
    node = event.get("node", node_name)
    event_type = event.get("type", "progress")
    status = event.get("status", "running")
    data = event.get("data", {})

    # 1. Validation 이벤트
    if node in ["nutrition_checker", "allergy_checker", "time_checker", "health_checker", "budget_checker"]:
        return {
            "type": "validation",
            "node": node,
            "status": status,
            "data": {
                "passed": data.get("passed", False),
                "reason": data.get("reason"),
            },
        }

    # 2. Meal Complete 이벤트
    if node == "validation_aggregator" and data.get("all_passed"):
        return {
            "type": "meal_complete",
            "node": node,
            "status": status,
            "data": data,  # Pass all data fields from validation_aggregator
        }

    # 3. Retry 이벤트
    if node == "retry_router":
        return {
            "type": "retry",
            "node": node,
            "status": status,
            "data": {
                "attempt": data.get("retry_count", 0),
                "reason": data.get("reason", "Validation failed"),
            },
        }

    # 4. 기본 Progress 이벤트
    return {
        "type": "progress",
        "node": node,
        "status": status,
        "data": data,  # Pass through all data fields from nodes
    }


def format_sse(event: dict) -> str:
    """
    SSE 형식 문자열 생성

    Args:
        event: 이벤트 딕셔너리

    Returns:
        SSE 형식 문자열 ("data: {json}\n\n")
    """
    json_str = json.dumps(event, ensure_ascii=False)
    return f"data: {json_str}\n\n"


def serialize_weekly_plan(weekly_plan: list) -> list:
    """
    주간 계획을 JSON 직렬화 가능한 형태로 변환

    Args:
        weekly_plan: DailyPlan 리스트

    Returns:
        직렬화된 주간 계획
    """
    return [
        {
            "day": day_plan.day,
            "meals": [
                {
                    "meal_type": menu.meal_type,
                    "recipe": {
                        "name": menu.menu_name,
                        "ingredients": menu.ingredients,
                        "instructions": menu.recipe_steps,
                        "cooking_time_min": menu.cooking_time_minutes,
                        "difficulty": "보통",  # Default difficulty
                        "estimated_cost": menu.estimated_cost,
                        "nutrition": {
                            "calories_kcal": menu.calories,
                            "protein_g": menu.protein_g,
                            "carbs_g": menu.carb_g,
                            "fat_g": menu.fat_g,
                            "sodium_mg": menu.sodium_mg,
                        },
                        "source": menu.recipe_url,
                    },
                    "budget_allocated": menu.estimated_cost,
                    "validation_status": {
                        "nutrition": "passed",
                        "allergy": "passed",
                        "time": "passed",
                        "health": "passed",
                        "budget": "passed",
                    },
                }
                for menu in day_plan.meals
            ],
            "total_nutrition": {
                "calories_kcal": day_plan.total_calories,
                "protein_g": day_plan.total_protein_g,
                "carbs_g": day_plan.total_carb_g,
                "fat_g": day_plan.total_fat_g,
                "sodium_mg": sum(menu.sodium_mg for menu in day_plan.meals),
            },
            "total_cost": day_plan.total_cost,
        }
        for day_plan in weekly_plan
    ]
