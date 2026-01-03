"""영양 목표 검증 노드"""
from app.models.state import MealPlanState, ValidationResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def nutrition_checker(state: MealPlanState) -> dict:
    """영양 목표 충족 검증 (칼로리 ±20% 허용)

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    menu = state["current_menu"]
    targets = state["per_meal_targets"]

    logger.info(
        "nutrition_checker_started",
        menu=menu.menu_name,
        target_calories=targets.calories,
        actual_calories=menu.calories,
    )

    logger.debug(
        "nutrition_checker_menu_details",
        calories=menu.calories,
        carb_g=menu.carb_g,
        protein_g=menu.protein_g,
        fat_g=menu.fat_g,
    )

    issues = []

    # Progressive relaxation: Retry count에 따라 점진적으로 완화
    retry_count = state.get("retry_count", 0)

    # Base tolerance
    calorie_tolerance = 0.2  # ±20%
    macro_tolerance = 0.3    # ±30%

    # Progressive relaxation (retry 3회 이상 시)
    if retry_count >= 3:
        calorie_tolerance = 0.25  # ±25%
        macro_tolerance = 0.35    # ±35%
        logger.info("progressive_relaxation_applied", retry_count=retry_count)

    # 칼로리 검증
    calorie_lower = targets.calories * (1 - calorie_tolerance)
    calorie_upper = targets.calories * (1 + calorie_tolerance)

    if not (calorie_lower <= menu.calories <= calorie_upper):
        tolerance_pct = int(calorie_tolerance * 100)
        issues.append(
            f"칼로리 범위 초과: 목표 {targets.calories:.0f}kcal (±{tolerance_pct}%), "
            f"실제 {menu.calories}kcal"
        )

    # 탄수화물 검증
    carb_lower = targets.carb_g * (1 - macro_tolerance)
    carb_upper = targets.carb_g * (1 + macro_tolerance)

    if not (carb_lower <= menu.carb_g <= carb_upper):
        tolerance_pct = int(macro_tolerance * 100)
        issues.append(
            f"탄수화물 범위 초과: 목표 {targets.carb_g:.0f}g (±{tolerance_pct}%), "
            f"실제 {menu.carb_g}g"
        )

    # 단백질 검증
    protein_lower = targets.protein_g * (1 - macro_tolerance)
    protein_upper = targets.protein_g * (1 + macro_tolerance)

    if not (protein_lower <= menu.protein_g <= protein_upper):
        tolerance_pct = int(macro_tolerance * 100)
        issues.append(
            f"단백질 범위 초과: 목표 {targets.protein_g:.0f}g (±{tolerance_pct}%), "
            f"실제 {menu.protein_g}g"
        )

    # 지방 검증
    fat_lower = targets.fat_g * (1 - macro_tolerance)
    fat_upper = targets.fat_g * (1 + macro_tolerance)

    if not (fat_lower <= menu.fat_g <= fat_upper):
        tolerance_pct = int(macro_tolerance * 100)
        issues.append(
            f"지방 범위 초과: 목표 {targets.fat_g:.0f}g (±{tolerance_pct}%), "
            f"실제 {menu.fat_g}g"
        )

    passed = len(issues) == 0

    result = ValidationResult(
        validator="nutrition_checker",
        passed=passed,
        issues=issues,
    )

    logger.info(
        "nutrition_checker_completed",
        passed=passed,
        issue_count=len(issues),
    )

    return {
        "validation_results": [result],
        "events": [{
            "type": "validation",
            "node": "nutrition_checker",
            "status": "completed",
            "data": {
                "passed": passed,
                "issues": issues,
            }
        }],
    }
