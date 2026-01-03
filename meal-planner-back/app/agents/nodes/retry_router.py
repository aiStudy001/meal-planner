"""Retry Router Node"""
from typing import Literal
from langgraph.types import Command
from app.models.state import MealPlanState
from app.utils.constants import RETRY_MAPPING
from app.utils.logging import get_logger

logger = get_logger(__name__)


def retry_router(state: MealPlanState) -> Command:
    """재시도 전략 라우팅 및 상태 업데이트

    retry_count에 따라 재시도 방식 결정:
    - retry_count == 0 (첫 실패): 실패한 검증기에 매핑된 특정 전문가로 라우팅
      * nutrition_checker 실패 → nutritionist
      * allergy_checker 실패 → chef
      * time_checker 실패 → chef
      * health_checker 실패 → nutritionist
      * budget_checker 실패 → budget
    - retry_count >= 1 (두 번째+ 실패): meal_planning_supervisor로 라우팅 (전체 재실행)

    conflict_resolver는 None인 추천을 이전 메뉴로 대체하므로
    특정 전문가만 재실행해도 정상 작동합니다.

    Args:
        state: 현재 그래프 상태

    Returns:
        Command 객체 (다음 노드 + 상태 업데이트)
    """
    retry_count = state["retry_count"]
    validation_results = state["validation_results"]
    failed_validators = [v.validator for v in validation_results if not v.passed]

    # 다음 노드 결정
    if retry_count == 0:
        # 첫 실패: 특정 전문가 재실행
        if not failed_validators:
            logger.error("retry_router_no_failures", retry_count=retry_count)
            next_node = "meal_planning_supervisor"
        else:
            first_failed = failed_validators[0]
            next_node = RETRY_MAPPING.get(first_failed, "meal_planning_supervisor")

            logger.info(
                "retry_router_specific_expert",
                retry_count=retry_count,
                failed_validator=first_failed,
                target_expert=next_node,
            )
    else:
        # 두 번째+ 실패: 전체 재실행
        next_node = "meal_planning_supervisor"

        logger.info(
            "retry_router_full_retry",
            retry_count=retry_count,
            target=next_node,
            failed_validators=failed_validators,
        )

    # 상태 업데이트 준비
    update = {
        "retry_count": retry_count + 1,
        "validation_results": [],  # 검증 결과 초기화
        "events": [{
            "type": "progress",
            "node": "retry_router",
            "status": "completed",
            "data": {
                "retry_count": retry_count + 1,
                "next_node": next_node,
            }
        }],
    }

    # 특정 전문가만 재실행하는 경우: 해당 전문가 추천만 초기화
    if retry_count == 0 and next_node in ["nutritionist", "chef", "budget"]:
        if next_node == "nutritionist":
            update["nutritionist_recommendation"] = None
        elif next_node == "chef":
            update["chef_recommendation"] = None
        elif next_node == "budget":
            update["budget_recommendation"] = None
    else:
        # 전체 재실행: 모든 추천 초기화
        update["nutritionist_recommendation"] = None
        update["chef_recommendation"] = None
        update["budget_recommendation"] = None

    # 상태 업데이트 + 다음 노드로 이동
    return Command(goto=next_node, update=update)
