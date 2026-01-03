"""예산 검증 노드

EC-024: 예산 초과 검증 with Progressive Relaxation
"""
from app.models.state import MealPlanState, ValidationResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def budget_checker(state: MealPlanState) -> dict:
    """예산 초과 검증 (Progressive Relaxation 적용)

    검증 기준:
    - retry 0-2: 예산의 110% 이하 허용
    - retry 3+: 예산의 115% 이하 허용

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    menu = state["current_menu"]
    budget = state["per_meal_budget"]
    retry_count = state.get("retry_count", 0)

    logger.info(
        "budget_checker_started",
        menu=menu.menu_name,
        budget=budget,
        actual_cost=menu.estimated_cost,
        retry_count=retry_count,
    )

    issues = []

    # Progressive relaxation: Retry count에 따라 점진적으로 완화
    if retry_count >= 3:
        over_budget_tolerance = 0.15  # 15% 초과 허용
        logger.info("progressive_relaxation_applied", retry_count=retry_count, tolerance="15%")
    else:
        over_budget_tolerance = 0.10  # 10% 초과 허용

    # 예산 상한선 계산
    budget_upper_limit = budget * (1 + over_budget_tolerance)

    # 예산 검증
    if menu.estimated_cost > budget_upper_limit:
        tolerance_pct = int(over_budget_tolerance * 100)
        over_amount = menu.estimated_cost - budget
        over_pct = ((menu.estimated_cost / budget) - 1) * 100

        issues.append(
            f"예산 초과: 목표 {budget:,}원 (+{tolerance_pct}% 허용), "
            f"실제 {menu.estimated_cost:,}원 "
            f"(+{over_pct:.1f}%, {over_amount:,}원 초과)"
        )

        logger.debug(
            "budget_constraint_violated",
            budget=budget,
            actual_cost=menu.estimated_cost,
            over_amount=over_amount,
            over_pct=over_pct,
            tolerance_pct=tolerance_pct,
        )

    passed = len(issues) == 0

    result = ValidationResult(
        validator="budget_checker",
        passed=passed,
        issues=issues,
    )

    logger.info(
        "budget_checker_completed",
        passed=passed,
        issue_count=len(issues),
    )

    return {
        "validation_results": [result],
        "events": [{
            "type": "validation",
            "node": "budget_checker",
            "status": "completed",
            "data": {
                "passed": passed,
                "issues": issues,
                "budget": budget,
                "actual_cost": menu.estimated_cost,
            }
        }],
    }
