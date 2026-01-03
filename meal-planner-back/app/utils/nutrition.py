"""영양 계산 유틸리티"""
from app.utils.constants import ACTIVITY_MULTIPLIERS, CALORIE_ADJUSTMENTS, MACRO_RATIOS


def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor 공식으로 BMR 계산

    Args:
        weight: 체중 (kg)
        height: 키 (cm)
        age: 나이
        gender: 성별 ("male" or "female")

    Returns:
        BMR (kcal/day)
    """
    if gender == "male":
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        return (10 * weight) + (6.25 * height) - (5 * age) - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """TDEE 계산

    Args:
        bmr: 기초대사량
        activity_level: 활동 수준 ("low", "moderate", "high", "very_high")

    Returns:
        TDEE (kcal/day)
    """
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return bmr * multiplier


def get_strictest_ratios(health_conditions: list[str]) -> dict[str, int]:
    """복수 질병이 있을 때 가장 엄격한 매크로 비율 선택

    Args:
        health_conditions: 질병 목록

    Returns:
        가장 엄격한 매크로 비율 dict
    """
    # 모든 질병의 비율을 가져옴
    all_ratios = [MACRO_RATIOS.get(condition) for condition in health_conditions if condition in MACRO_RATIOS]

    if not all_ratios:
        return MACRO_RATIOS["유지"]

    # 탄수화물은 가장 낮은 값, 단백질은 가장 높은 값 선택
    return {
        "carb": min(r["carb"] for r in all_ratios),
        "protein": max(r["protein"] for r in all_ratios),
        "fat": max(r["fat"] for r in all_ratios),
    }


def calculate_daily_totals(meals: list) -> dict:
    """하루 식단의 영양 총합 계산

    Args:
        meals: Menu 객체 리스트

    Returns:
        일일 영양 총합 dict
    """
    return {
        "total_calories": sum(m.calories for m in meals),
        "total_carb_g": sum(m.carb_g for m in meals),
        "total_protein_g": sum(m.protein_g for m in meals),
        "total_fat_g": sum(m.fat_g for m in meals),
        "total_sodium_mg": sum(m.sodium_mg for m in meals),
        "total_sugar_g": sum(m.sugar_g for m in meals),
        "total_cost": sum(m.estimated_cost for m in meals),
    }
