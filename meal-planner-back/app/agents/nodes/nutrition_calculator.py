"""영양 계산 노드"""
from app.models.state import MealPlanState, MacroTargets
from app.utils.constants import ACTIVITY_MULTIPLIERS, CALORIE_ADJUSTMENTS, MACRO_RATIOS, MEAL_TYPES, BUDGET_RATIOS
from app.utils.nutrition import calculate_bmr, calculate_tdee, get_strictest_ratios
from app.utils.logging import get_logger

logger = get_logger(__name__)


def calculate_daily_targets(profile) -> MacroTargets:
    """일일 영양 목표 계산"""
    bmr = calculate_bmr(profile.weight, profile.height, profile.age, profile.gender)
    tdee = calculate_tdee(bmr, profile.activity_level)

    # 칼로리 조정
    adjustment = profile.calorie_adjustment or CALORIE_ADJUSTMENTS.get(profile.goal, 0)
    daily_calories = tdee + adjustment

    # 매크로 비율 결정
    if profile.health_conditions:
        ratios = get_strictest_ratios(profile.health_conditions)
    else:
        ratios = MACRO_RATIOS.get(profile.goal, MACRO_RATIOS["유지"])

    logger.info(
        "daily_targets_calculated",
        bmr=bmr,
        tdee=tdee,
        daily_calories=daily_calories,
        ratios=ratios,
    )

    return MacroTargets(
        calories=daily_calories,
        carb_g=(daily_calories * ratios["carb"] / 100) / 4,
        protein_g=(daily_calories * ratios["protein"] / 100) / 4,
        fat_g=(daily_calories * ratios["fat"] / 100) / 9,
        carb_ratio=ratios["carb"],
        protein_ratio=ratios["protein"],
        fat_ratio=ratios["fat"],
    )


def calculate_per_meal_targets(daily: MacroTargets, meals_per_day: int) -> MacroTargets:
    """끼니당 영양 목표 계산 (균등 배분)"""
    return MacroTargets(
        calories=daily.calories / meals_per_day,
        carb_g=daily.carb_g / meals_per_day,
        protein_g=daily.protein_g / meals_per_day,
        fat_g=daily.fat_g / meals_per_day,
        carb_ratio=daily.carb_ratio,
        protein_ratio=daily.protein_ratio,
        fat_ratio=daily.fat_ratio,
    )


def get_meal_types_for_day(meals_per_day: int) -> list[str]:
    """끼니 수에 따른 끼니 타입 반환"""
    if meals_per_day == 1:
        return ["점심"]
    elif meals_per_day == 2:
        return ["아침", "저녁"]
    elif meals_per_day == 3:
        return ["아침", "점심", "저녁"]
    else:  # 4
        return ["아침", "점심", "저녁", "간식"]


def calculate_per_meal_budgets(
    budget: int,
    budget_type: str,
    budget_distribution: str,
    meals_per_day: int,
    days: int
) -> tuple[int, dict[str, int] | None]:
    """끼니별 예산 계산
    
    Returns:
        tuple: (평균 끼니당 예산, 끼니별 예산 딕셔너리 또는 None)
    """
    # 총 예산 계산
    if budget_type == "weekly":
        total_budget = budget
    elif budget_type == "daily":
        total_budget = budget * days
    else:  # per_meal
        total_meals = meals_per_day * days
        total_budget = budget * total_meals

    total_meals = meals_per_day * days
    per_meal_budget = total_budget // total_meals

    # 균등 배분
    if budget_distribution == "equal":
        return per_meal_budget, None

    # 차등 배분
    meal_types = get_meal_types_for_day(meals_per_day)
    daily_budget = total_budget / days
    
    # 가중치 합 계산
    total_ratio = sum(BUDGET_RATIOS[meal_type] for meal_type in meal_types)
    
    # 끼니별 예산 계산
    per_meal_budgets = {
        meal_type: int((daily_budget * BUDGET_RATIOS[meal_type]) / total_ratio)
        for meal_type in meal_types
    }
    
    logger.info(
        "budget_distribution_calculated",
        distribution=budget_distribution,
        per_meal_budgets=per_meal_budgets,
        total_ratio=total_ratio,
    )
    
    return per_meal_budget, per_meal_budgets


async def nutrition_calculator(state: MealPlanState) -> dict:
    """BMR/TDEE/매크로 목표 계산

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    profile = state["profile"]

    logger.info(
        "nutrition_calculator_started",
        goal=profile.goal,
        weight=profile.weight,
        height=profile.height,
        age=profile.age,
        gender=profile.gender,
    )

    daily_targets = calculate_daily_targets(profile)
    per_meal_targets = calculate_per_meal_targets(daily_targets, profile.meals_per_day)

    # 예산 계산 (균등 또는 차등 배분)
    per_meal_budget, per_meal_budgets = calculate_per_meal_budgets(
        budget=profile.budget,
        budget_type=profile.budget_type,
        budget_distribution=profile.budget_distribution,
        meals_per_day=profile.meals_per_day,
        days=profile.days
    )

    logger.info(
        "nutrition_calculator_completed",
        daily_calories=daily_targets.calories,
        per_meal_calories=per_meal_targets.calories,
        per_meal_budget=per_meal_budget,
        budget_distribution=profile.budget_distribution,
        per_meal_budgets=per_meal_budgets,
    )

    # 첫 끼니 타입 결정
    meal_types = get_meal_types_for_day(profile.meals_per_day)
    first_meal_type = meal_types[0]

    return {
        "daily_targets": daily_targets,
        "per_meal_targets": per_meal_targets,
        "per_meal_budget": per_meal_budget,
        "per_meal_budgets": per_meal_budgets,
        "current_day": 1,
        "current_meal_index": 0,
        "current_meal_type": first_meal_type,
        "retry_count": 0,
        "completed_meals": [],
        "weekly_plan": [],
        "events": [{
            "type": "progress",
            "node": "nutrition_calculator",
            "status": "completed",
            "data": {
                "daily_calories": daily_targets.calories,
                "per_meal_calories": per_meal_targets.calories,
                "budget_distribution": profile.budget_distribution,
                "day": 1,
                "meal": 1,
                "meal_type": first_meal_type,
            }
        }],
    }
