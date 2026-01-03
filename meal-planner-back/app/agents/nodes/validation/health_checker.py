"""건강 제약 조건 검증 노드

EC-023: 당뇨, 고혈압, 고지혈증 등 건강 조건에 따른 메뉴 검증
"""
from app.models.state import MealPlanState, ValidationResult
from app.utils.logging import get_logger

logger = get_logger(__name__)

# 건강 조건별 기준값
HEALTH_CONSTRAINTS = {
    "당뇨": {
        "sugar_g_max": 30,  # 당류 최대 30g
        "description": "당류 제한 (최대 30g)"
    },
    "고혈압": {
        "sodium_mg_max": 2000,  # 나트륨 최대 2000mg
        "description": "나트륨 제한 (최대 2000mg)"
    },
    "고지혈증": {
        "saturated_fat_g_max": 7,  # 포화지방 최대 7g (estimated)
        "description": "포화지방 제한 (최대 7g, 추정)"
    }
}


async def health_checker(state: MealPlanState) -> dict:
    """건강 제약 조건 검증

    검증 항목:
    - 당뇨: sugar_g ≤ 30g (현재는 추정값, 향후 정확한 당류 정보 필요)
    - 고혈압: sodium_mg ≤ 2000mg
    - 고지혈증: saturated_fat_g ≤ 7g (fat_g의 30%로 추정)

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    menu = state["current_menu"]
    profile = state["profile"]
    health_conditions = profile.health_conditions or []

    logger.info(
        "health_checker_started",
        menu=menu.menu_name,
        health_conditions=health_conditions,
    )

    issues = []

    # 건강 조건이 없으면 자동 통과
    if not health_conditions:
        logger.info("health_checker_no_conditions", passed=True)
        result = ValidationResult(
            validator="health_checker",
            passed=True,
            issues=[],
        )
        return {
            "validation_results": [result],
            "events": [{
                "type": "validation",
                "node": "health_checker",
                "status": "completed",
                "data": {
                    "passed": True,
                    "issues": [],
                }
            }],
        }

    # 각 건강 조건 검증
    for condition in health_conditions:
        if condition not in HEALTH_CONSTRAINTS:
            logger.warning("unknown_health_condition", condition=condition)
            continue

        constraint = HEALTH_CONSTRAINTS[condition]

        # 당뇨: 당류 제한 (현재는 탄수화물의 30%로 추정)
        if condition == "당뇨" and menu.carb_g is not None:
            estimated_sugar_g = menu.carb_g * 0.3  # 탄수화물의 30%를 당류로 추정
            max_sugar = constraint["sugar_g_max"]

            if estimated_sugar_g > max_sugar:
                issues.append(
                    f"당뇨 제약: 추정 당류 {estimated_sugar_g:.1f}g "
                    f"(탄수화물 {menu.carb_g}g의 30%) > 기준 {max_sugar}g"
                )
                logger.debug(
                    "diabetes_constraint_violated",
                    estimated_sugar_g=estimated_sugar_g,
                    max_allowed=max_sugar,
                )

        # 고혈압: 나트륨 제한
        if condition == "고혈압" and menu.sodium_mg is not None:
            max_sodium = constraint["sodium_mg_max"]

            if menu.sodium_mg > max_sodium:
                issues.append(
                    f"고혈압 제약: 나트륨 {menu.sodium_mg}mg > 기준 {max_sodium}mg"
                )
                logger.debug(
                    "hypertension_constraint_violated",
                    sodium_mg=menu.sodium_mg,
                    max_allowed=max_sodium,
                )

        # 고지혈증: 포화지방 제한 (전체 지방의 30%로 추정)
        if condition == "고지혈증" and menu.fat_g is not None:
            estimated_saturated_fat_g = menu.fat_g * 0.3  # 지방의 30%를 포화지방으로 추정
            max_saturated_fat = constraint["saturated_fat_g_max"]

            if estimated_saturated_fat_g > max_saturated_fat:
                issues.append(
                    f"고지혈증 제약: 추정 포화지방 {estimated_saturated_fat_g:.1f}g "
                    f"(지방 {menu.fat_g}g의 30%) > 기준 {max_saturated_fat}g"
                )
                logger.debug(
                    "hyperlipidemia_constraint_violated",
                    estimated_saturated_fat_g=estimated_saturated_fat_g,
                    max_allowed=max_saturated_fat,
                )

    passed = len(issues) == 0

    result = ValidationResult(
        validator="health_checker",
        passed=passed,
        issues=issues,
    )

    logger.info(
        "health_checker_completed",
        passed=passed,
        issue_count=len(issues),
        health_conditions=health_conditions,
    )

    return {
        "validation_results": [result],
        "events": [{
            "type": "validation",
            "node": "health_checker",
            "status": "completed",
            "data": {
                "passed": passed,
                "issues": issues,
                "health_conditions": health_conditions,
            }
        }],
    }
