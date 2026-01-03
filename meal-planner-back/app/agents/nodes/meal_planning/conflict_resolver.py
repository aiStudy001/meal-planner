"""Conflict Resolver (3명 의견 통합)"""
from app.models.state import MealPlanState, Menu
from app.services.llm_service import get_llm_service, parse_json_response
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def conflict_resolver(state: MealPlanState) -> dict:
    """3명의 전문가 의견을 통합하여 최종 메뉴 결정

    재시도 시나리오 지원:
    - None인 추천은 이전 메뉴 정보로 대체 (특정 전문가만 재실행 시)
    - 모든 추천이 있으면 3명 의견 통합
    - 일부만 있으면 해당 전문가 의견 우선 반영

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    nutritionist = state.get("nutritionist_recommendation")
    chef = state.get("chef_recommendation")
    budget = state.get("budget_recommendation")
    profile = state["profile"]
    targets = state["per_meal_targets"]
    current_menu = state.get("current_menu")

    # CRITICAL: Early validation - 모든 추천이 None이고 첫 끼니인 경우
    from app.models.state import MealRecommendation

    if all(rec is None for rec in [nutritionist, chef, budget]):
        if current_menu is None:
            # Emergency fallback for first meal with all failures
            logger.error(
                "all_recommendations_none_first_meal",
                day=state["current_day"],
                meal_type=state["current_meal_type"],
                retry_count=state.get("retry_count", 0)
            )

            # Create emergency fallback menu
            fallback_menu = Menu(
                meal_type=state["current_meal_type"],
                menu_name="기본 식단 (재시도 필요)",
                ingredients=[
                    {"name": "현미밥", "amount": "210g", "amount_g": 210.0},
                    {"name": "계란", "amount": "1개", "amount_g": 50.0},
                ],
                calories=500,
                carb_g=70,
                protein_g=15,
                fat_g=10,
                sodium_mg=400,
                sugar_g=5,
                cooking_time_minutes=10,
                estimated_cost=3000,
                recipe_steps=[
                    "시스템 오류로 기본 식단이 제공되었습니다.",
                    "재시도를 권장합니다."
                ]
            )

            return {
                "current_menu": fallback_menu,
                "validation_results": [],  # Reset validation results for new meal
                "events": [{
                    "type": "error",
                    "node": "conflict_resolver",
                    "status": "fallback",
                    "data": {
                        "message": "모든 전문가 추천 실패, 기본 식단 제공",
                        "menu": fallback_menu.menu_name
                    }
                }]
            }
        else:
            # Keep previous menu
            logger.warning(
                "all_recommendations_none_keep_previous",
                day=state["current_day"],
                meal_type=state["current_meal_type"],
                previous_menu=current_menu.menu_name
            )
            return {
                "current_menu": current_menu,
                "validation_results": [],  # Reset validation results for new meal
                "events": [{
                    "type": "warning",
                    "node": "conflict_resolver",
                    "status": "reused_previous",
                    "data": {
                        "message": "모든 전문가 추천 실패, 이전 메뉴 재사용",
                        "menu": current_menu.menu_name
                    }
                }]
            }

    # None인 추천을 이전 메뉴로 대체 (재시도 시)
    if nutritionist is None and current_menu:
        nutritionist = MealRecommendation(
            menu_name=current_menu.menu_name,
            ingredients=current_menu.ingredients,
            estimated_calories=current_menu.calories,
            estimated_cost=current_menu.estimated_cost,
            cooking_time_minutes=current_menu.cooking_time_minutes,
            reasoning="(이전 메뉴 재사용)"
        )

    if chef is None and current_menu:
        chef = MealRecommendation(
            menu_name=current_menu.menu_name,
            ingredients=current_menu.ingredients,
            estimated_calories=current_menu.calories,
            estimated_cost=current_menu.estimated_cost,
            cooking_time_minutes=current_menu.cooking_time_minutes,
            reasoning="(이전 메뉴 재사용)"
        )

    if budget is None and current_menu:
        budget = MealRecommendation(
            menu_name=current_menu.menu_name,
            ingredients=current_menu.ingredients,
            estimated_calories=current_menu.calories,
            estimated_cost=current_menu.estimated_cost,
            cooking_time_minutes=current_menu.cooking_time_minutes,
            reasoning="(이전 메뉴 재사용)"
        )

    logger.info(
        "conflict_resolver_started",
        nutritionist_menu=nutritionist.menu_name if nutritionist else None,
        chef_menu=chef.menu_name if chef else None,
        budget_menu=budget.menu_name if budget else None,
        has_previous_menu=current_menu is not None,
    )

    prompt = f"""당신은 식단 기획 총괄 매니저입니다.

3명의 전문가가 각자의 관점에서 메뉴를 추천했습니다.
이를 종합하여 최적의 메뉴 1개를 결정해주세요.

## 전문가 추천

### 영양사 추천
- 메뉴: {nutritionist.menu_name}
- 예상 칼로리: {nutritionist.estimated_calories}kcal
- 예상 비용: {nutritionist.estimated_cost:,}원
- 조리 시간: {nutritionist.cooking_time_minutes}분
- 추천 이유: {nutritionist.reasoning}

### 셰프 추천
- 메뉴: {chef.menu_name}
- 예상 칼로리: {chef.estimated_calories}kcal
- 예상 비용: {chef.estimated_cost:,}원
- 조리 시간: {chef.cooking_time_minutes}분
- 추천 이유: {chef.reasoning}

### 예산 전문가 추천
- 메뉴: {budget.menu_name}
- 예상 칼로리: {budget.estimated_calories}kcal
- 예상 비용: {budget.estimated_cost:,}원
- 조리 시간: {budget.cooking_time_minutes}분
- 추천 이유: {budget.reasoning}

## 결정 기준 (우선순위)
1. 영양 목표 충족 (칼로리 {targets.calories:.0f}kcal ±20%)
2. 알레르기 성분 배제: {', '.join(profile.restrictions) or '없음'}
3. 조리 시간 준수: {profile.cooking_time}
4. 예산 준수: {state["per_meal_budget"]:,}원

위 기준을 모두 만족하는 메뉴를 선택하거나,
전문가들의 의견을 조합한 새로운 메뉴를 제안해주세요.

## 출력 형식 (JSON)
**중요: 반드시 아래 모든 필드를 포함해야 합니다.**
**숫자는 쉼표 없이 정수/실수로만 작성하세요. (예: 5000, 60.5)**

{{
    "menu_name": "최종 메뉴명",
    "ingredients": [{{"name": "재료명", "amount": "100g"}}],
    "calories": 500,
    "carb_g": 60,
    "protein_g": 30,
    "fat_g": 15,
    "sodium_mg": 500,
    "sugar_g": 10,
    "cooking_time_minutes": 20,
    "estimated_cost": 5000,
    "recipe_steps": ["1단계", "2단계", "3단계"]
}}

**필수 필드**: menu_name, ingredients, calories, carb_g, protein_g, fat_g, sodium_mg, sugar_g, cooking_time_minutes, estimated_cost, recipe_steps
"""

    llm_service = get_llm_service()
    try:
        response = await llm_service.ainvoke(prompt)
        logger.debug("conflict_resolver_llm_response", response=response)
        menu_data = parse_json_response(response)
        logger.debug("conflict_resolver_parsed_data", data=menu_data)

        current_menu = Menu(
            meal_type=state["current_meal_type"],
            **menu_data
        )

        logger.info(
            "conflict_resolver_completed",
            final_menu=current_menu.menu_name,
            calories=current_menu.calories,
            cost=current_menu.estimated_cost,
        )

        return {
            "current_menu": current_menu,
            "validation_results": [],  # Reset validation results for new meal
            "events": [{
                "type": "progress",
                "node": "conflict_resolver",
                "status": "completed",
                "data": {
                    "menu": current_menu.menu_name,
                    "calories": current_menu.calories,
                    "day": state.get("current_day"),
                    "meal": state.get("current_meal_index", 0) + 1,
                    "meal_type": state.get("current_meal_type"),
                }
            }],
        }
    except Exception as e:
        logger.error("conflict_resolver_failed", error=str(e))
        raise
