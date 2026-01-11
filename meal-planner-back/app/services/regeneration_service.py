"""
특정 끼니 재생성 서비스

기존 식단의 특정 끼니만 재생성하는 로직을 제공
"""

from typing import Dict
from app.models.requests import RegenerateMealRequest
from app.models.state import MealPlanState, MacroTargets
from app.utils.logging import get_logger

logger = get_logger(__name__)


def calculate_meal_nutrition_targets(
    daily_targets: dict,
    meal_type: str,
    budget_distribution: str
) -> Dict[str, float]:
    """
    끼니별 영양 목표 계산

    Args:
        daily_targets: 일일 영양 목표 {"calories": 1800, "carb_g": 225, ...}
        meal_type: 끼니 타입 (아침, 점심, 저녁, 간식)
        budget_distribution: 예산 배분 방식 (equal, weighted)

    Returns:
        끼니별 영양 목표 딕셔너리
    """
    # 끼니별 비율 정의
    ratios = {
        "weighted": {
            "아침": 0.25,
            "점심": 0.35,
            "저녁": 0.40,
            "간식": 0.10
        },
        "equal": {
            "아침": 0.33,
            "점심": 0.33,
            "저녁": 0.33,
            "간식": 0.10
        }
    }

    # 배분 방식에 따른 비율 선택
    ratio_map = ratios.get(budget_distribution, ratios["equal"])
    ratio = ratio_map.get(meal_type, 0.33)

    # 각 영양소에 비율 적용
    meal_targets = {}
    for key, value in daily_targets.items():
        if isinstance(value, (int, float)):
            meal_targets[key] = value * ratio
        else:
            meal_targets[key] = value

    logger.info(
        "meal_nutrition_targets_calculated",
        meal_type=meal_type,
        ratio=ratio,
        targets=meal_targets
    )

    return meal_targets


def build_regeneration_state(request: RegenerateMealRequest) -> MealPlanState:
    """
    단일 끼니 재생성용 초기 상태 생성

    Args:
        request: 재생성 요청 (프로필, 대상 끼니, 컨텍스트 포함)

    Returns:
        MealPlanState: LangGraph 실행을 위한 초기 상태

    Notes:
        - 기존 식단의 특정 끼니만 재생성
        - 다른 끼니들은 completed_meals_context로 전달
        - 중복 방지를 위해 recently_used_recipes 포함
    """
    profile = request.profile

    # 끼니별 영양 목표 계산
    meal_nutrition_targets = calculate_meal_nutrition_targets(
        daily_targets=request.daily_nutrition_targets,
        meal_type=request.target_meal_type,
        budget_distribution=profile.budget_distribution
    )

    # MacroTargets 객체 생성 (LangGraph state 스키마 호환)
    # 비율 계산 (기존 daily_targets 기반)
    total_macros = (
        request.daily_nutrition_targets.get("carb_g", 0) +
        request.daily_nutrition_targets.get("protein_g", 0) +
        request.daily_nutrition_targets.get("fat_g", 0)
    )

    if total_macros > 0:
        carb_ratio = int((request.daily_nutrition_targets.get("carb_g", 0) / total_macros) * 100)
        protein_ratio = int((request.daily_nutrition_targets.get("protein_g", 0) / total_macros) * 100)
        fat_ratio = 100 - carb_ratio - protein_ratio
    else:
        # 기본 비율 (50/30/20)
        carb_ratio, protein_ratio, fat_ratio = 50, 30, 20

    per_meal_targets = MacroTargets(
        calories=meal_nutrition_targets.get("calories", 0),
        carb_g=meal_nutrition_targets.get("carb_g", 0),
        protein_g=meal_nutrition_targets.get("protein_g", 0),
        fat_g=meal_nutrition_targets.get("fat_g", 0),
        carb_ratio=carb_ratio,
        protein_ratio=protein_ratio,
        fat_ratio=fat_ratio
    )

    # 일일 목표도 MacroTargets로 변환
    daily_targets = MacroTargets(
        calories=request.daily_nutrition_targets.get("calories", 0),
        carb_g=request.daily_nutrition_targets.get("carb_g", 0),
        protein_g=request.daily_nutrition_targets.get("protein_g", 0),
        fat_g=request.daily_nutrition_targets.get("fat_g", 0),
        carb_ratio=carb_ratio,
        protein_ratio=protein_ratio,
        fat_ratio=fat_ratio
    )

    # current_meal_index 계산 (하루 끼니 순서)
    meal_order = ["아침", "점심", "저녁", "간식"]
    try:
        current_meal_index = meal_order.index(request.target_meal_type)
    except ValueError:
        current_meal_index = 0

    # 초기 상태 생성
    initial_state: MealPlanState = {
        "profile": profile,
        "daily_targets": daily_targets,
        "per_meal_targets": per_meal_targets,
        "per_meal_budget": request.per_meal_budget,
        "per_meal_budgets": None,  # 단일 끼니 재생성에서는 사용 안 함
        "current_day": request.target_day,
        "current_meal_type": request.target_meal_type,
        "current_meal_index": current_meal_index,
        "nutritionist_recommendation": None,
        "chef_recommendation": None,
        "budget_recommendation": None,
        "current_menu": None,
        "validation_results": [],
        "retry_count": 0,
        "max_retries": 5,
        "error_message": None,
        "completed_meals": [],  # 재생성 후 새 메뉴가 추가됨
        "weekly_plan": [],
        "events": [],
        "previous_validation_failures": [],  # 검증 실패 히스토리
    }

    logger.info(
        "regeneration_state_built",
        target_day=request.target_day,
        target_meal_type=request.target_meal_type,
        per_meal_budget=request.per_meal_budget,
        meal_targets=meal_nutrition_targets,
        recently_used_count=len(request.recently_used_recipes),
        context_meals_count=len(request.completed_meals_context)
    )

    return initial_state


def extract_used_ingredients(completed_meals: list[dict]) -> list[str]:
    """
    완료된 끼니에서 사용된 주재료 추출

    Args:
        completed_meals: 완료된 끼니 목록

    Returns:
        사용된 주재료 이름 리스트
    """
    ingredients = []
    for meal in completed_meals:
        # Assuming meal has a "menu_name" field
        # In real implementation, you might want to parse ingredients from recipe
        # For now, we'll extract from menu_name
        menu_name = meal.get("menu_name", "")
        # Simple extraction: split by common delimiters
        parts = menu_name.replace("(", " ").replace(")", " ").split()
        ingredients.extend(parts)

    # Remove duplicates and return
    return list(set(ingredients))
