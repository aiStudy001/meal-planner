"""Decision Maker Node"""
from typing import Literal
from app.models.state import MealPlanState
from app.utils.logging import get_logger

logger = get_logger(__name__)


def decision_maker(state: MealPlanState) -> Literal["day_iterator", "retry_router"]:
    """검증 결과 기반 라우팅 결정

    검증 결과를 분석하여 다음 단계를 결정합니다:
    - 모든 검증 통과 → "day_iterator" (다음 끼니/날짜로 진행)
    - 일부 검증 실패 + 재시도 가능 → "retry_router" (재시도 로직으로 이동)
    - 일부 검증 실패 + 재시도 한계 → "day_iterator" (실패 받아들이고 진행)

    Args:
        state: 현재 그래프 상태

    Returns:
        다음 노드 이름
    """
    validation_results = state["validation_results"]
    failed_validators = [v for v in validation_results if not v.passed]
    retry_count = state["retry_count"]
    max_retries = state["max_retries"]

    all_passed = len(failed_validators) == 0

    if all_passed:
        logger.info(
            "decision_maker_route_success",
            route="day_iterator",
            menu=state["current_menu"].menu_name,
        )
        return "day_iterator"
    elif retry_count >= max_retries:
        # 재시도 한계 도달: 검증 실패를 경고로 기록하고 진행
        # 실패한 검증 내용을 수집
        warning_messages = []
        for v in failed_validators:
            validator_name = v.validator
            issues = v.issues if v.issues else ["검증 실패 (상세 정보 없음)"]
            for issue in issues:
                warning_messages.append(f"[{validator_name}] {issue}")

        logger.warning(
            "decision_maker_max_retries_reached",
            route="day_iterator",
            retry_count=retry_count,
            max_retries=max_retries,
            failed_validators=[v.validator for v in failed_validators],
            menu=state["current_menu"].menu_name,
            warnings=warning_messages,
        )

        # 상태에 경고 메시지 저장 (day_iterator에서 사용)
        state["_validation_warnings"] = warning_messages

        return "day_iterator"
    else:
        # 재시도 가능
        logger.info(
            "decision_maker_route_retry",
            route="retry_router",
            failed_count=len(failed_validators),
            failed_validators=[v.validator for v in failed_validators],
            retry_count=retry_count,
            max_retries=max_retries,
        )
        return "retry_router"
