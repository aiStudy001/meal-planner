"""알레르기 및 제외 성분 검증 노드"""
from app.models.state import MealPlanState, ValidationResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def allergy_checker(state: MealPlanState) -> dict:
    """알레르기 및 제외 식품 검증

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    menu = state["current_menu"]
    profile = state["profile"]
    restrictions = profile.restrictions

    logger.info(
        "allergy_checker_started",
        menu=menu.menu_name,
        restrictions=restrictions,
    )

    issues = []

    if not restrictions:
        # 제한 사항이 없으면 자동 통과
        result = ValidationResult(
            validator="allergy_checker",
            passed=True,
            reason="제한 사항이 없습니다.",
        )

        logger.info("allergy_checker_completed", passed=True, no_restrictions=True)

        return {
            "validation_results": [result],
            "events": [{
                "type": "validation",
                "node": "allergy_checker",
                "status": "completed",
                "data": {"passed": True, "issues": []}
            }],
        }

    # 각 재료를 제한 사항과 비교
    for ingredient in menu.ingredients:
        ingredient_name = ingredient["name"].lower()

        for restriction in restrictions:
            restriction_lower = restriction.lower()

            # 포함 여부 체크 (부분 문자열 매칭)
            if restriction_lower in ingredient_name or ingredient_name in restriction_lower:
                issues.append(
                    f"제한 식품 포함: '{ingredient['name']}' (제한: {restriction})"
                )
                logger.warning(
                    "allergy_violation_detected",
                    ingredient=ingredient["name"],
                    restriction=restriction,
                )

    passed = len(issues) == 0

    result = ValidationResult(
        validator="allergy_checker",
        passed=passed,
        reason="; ".join(issues) if issues else "알레르기 성분이 포함되지 않았습니다.",
        details={"issues": issues},
    )

    logger.info(
        "allergy_checker_completed",
        passed=passed,
        issue_count=len(issues),
    )

    return {
        "validation_results": [result],
        "events": [{
            "type": "validation",
            "node": "allergy_checker",
            "status": "completed",
            "data": {
                "passed": passed,
                "issues": issues,
            }
        }],
    }
