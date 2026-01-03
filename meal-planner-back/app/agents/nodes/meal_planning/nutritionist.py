"""영양사 에이전트"""
from json import JSONDecodeError

from pydantic import ValidationError

from app.models.state import MealPlanState, MealRecommendation
from app.services.llm_service import get_llm_service, parse_json_response
from app.services.recipe_search import get_recipe_search_service
from app.utils.constants import ENABLE_RECIPE_SEARCH
from app.utils.logging import get_logger
from app.utils.prompt_safety import escape_for_llm

logger = get_logger(__name__)


async def nutritionist_agent(state: MealPlanState) -> dict:
    """영양사 에이전트: 영양 균형 관점에서 메뉴 추천

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    profile = state["profile"]
    targets = state["per_meal_targets"]

    # 이전 실패 이력 가져오기
    previous_failures = state.get("previous_validation_failures", [])
    retry_count = state.get("retry_count", 0)

    logger.info(
        "nutritionist_started",
        meal_type=state["current_meal_type"],
        day=state["current_day"],
        target_calories=targets.calories,
    )

    # Recipe search enhancement - provide real nutrition data as reference
    recipe_context = ""
    if ENABLE_RECIPE_SEARCH:
        search_service = get_recipe_search_service()
        try:
            search_query = f"{state['current_meal_type']} {profile.goal}"
            if profile.restrictions:
                search_query += f" exclude:{','.join(profile.restrictions[:2])}"

            recipes = await search_service.search_recipes(
                query=search_query,
                filters={
                    "target_calories": targets.calories,
                    "calorie_tolerance": 0.3,
                    "exclude_ingredients": profile.restrictions,
                },
            )

            if recipes:
                recipe_context = "\n## 참고 레시피 (실제 영양 데이터)\n"
                for i, recipe in enumerate(recipes[:3], 1):
                    recipe_context += f"\n### 레시피 {i}: {recipe['name']}\n"
                    recipe_context += f"- 칼로리: {recipe.get('calories', 'N/A')}kcal\n"
                    recipe_context += f"- 탄수화물: {recipe.get('carb_g', 'N/A')}g\n"
                    recipe_context += f"- 단백질: {recipe.get('protein_g', 'N/A')}g\n"
                    recipe_context += f"- 지방: {recipe.get('fat_g', 'N/A')}g\n"
                    recipe_context += f"- 재료: {', '.join(recipe.get('ingredients', [])[:5])}\n"

                logger.info("recipe_search_success", count=len(recipes))
        except Exception as e:
            logger.warning("recipe_search_failed", error=str(e))

    # 건강 상태별 추가 고려사항
    health_notes = []
    if "당뇨" in profile.health_conditions:
        health_notes.append("- 당류 25g 이하, 저GI 식품 선호")
    if "고혈압" in profile.health_conditions:
        health_notes.append("- 나트륨 667mg 이하 (1끼니)")
    if "고지혈증" in profile.health_conditions:
        health_notes.append("- 포화지방 5g 이하 (1끼니)")

    prompt = f"""당신은 전문 영양사입니다.

다음 조건에 맞는 {state["current_meal_type"]} 메뉴 1개를 추천해주세요.

## 영양 목표 (1끼니 기준)
- 칼로리: {targets.calories:.0f}kcal
- 탄수화물: {targets.carb_g:.0f}g
- 단백질: {targets.protein_g:.0f}g
- 지방: {targets.fat_g:.0f}g

## 제한 사항
- 알레르기/제외 식품: {', '.join(escape_for_llm(r) for r in profile.restrictions) if profile.restrictions else '없음'}
- 건강 상태: {', '.join(escape_for_llm(h) for h in profile.health_conditions) if profile.health_conditions else '없음'}

## 추가 고려사항
{chr(10).join(health_notes) if health_notes else '없음'}

{recipe_context}

영양 균형을 최우선으로 고려하여 메뉴를 추천해주세요.
{recipe_context and "위 참고 레시피의 실제 영양 데이터를 활용하거나 유사한 영양 구성을 참고하세요." or ""}"""

    # 피드백 섹션 생성
    feedback_section = ""
    if retry_count > 0 and previous_failures:
        # 영양사 관련 실패만 필터링
        nutrition_failures = [
            f for f in previous_failures
            if f.get("validator") == "nutrition_checker" and f.get("retry_count") == retry_count - 1
        ]

        if nutrition_failures:
            feedback_section = "\n\n## ⚠️ 이전 시도 피드백\n"
            feedback_section += f"**재시도 {retry_count}회차**: 이전 메뉴가 다음 이유로 실패했습니다.\n\n"

            for failure in nutrition_failures:
                feedback_section += f"### 메뉴: {failure.get('menu_name', 'Unknown')}\n"
                for issue in failure.get("issues", []):
                    feedback_section += f"- {issue}\n"
                feedback_section += "\n"

            feedback_section += "**중요**: 위 문제를 해결하도록 영양 성분을 조정해주세요.\n"
            feedback_section += "특히 초과/부족한 영양소를 목표 범위 내로 맞춰주세요.\n"

            logger.info(
                "retry_with_feedback",
                retry_count=retry_count,
                previous_failures_count=len(previous_failures),
                nutrition_failures_count=len(nutrition_failures),
                feedback_provided=True,
            )

    prompt += feedback_section

    prompt += """

## 출력 형식 (JSON)
**중요: 반드시 아래 모든 필드를 포함해야 합니다.**
**숫자는 쉼표 없이 정수로만 작성하세요. (예: 5000, 500)**

{{
    "menu_name": "메뉴명",
    "ingredients": [{{"name": "재료명", "amount": "100g"}}],
    "estimated_calories": 500,
    "estimated_cost": 5000,
    "cooking_time_minutes": 20,
    "reasoning": "추천 이유"
}}

**필수 필드**: menu_name, ingredients, estimated_calories, estimated_cost, cooking_time_minutes, reasoning
"""

    llm_service = get_llm_service()
    try:
        response = await llm_service.ainvoke(prompt)
        logger.debug("nutritionist_llm_response", response=response)
        recommendation_data = parse_json_response(response)
        logger.debug("nutritionist_parsed_data", data=recommendation_data)
        recommendation = MealRecommendation(**recommendation_data)

        logger.info(
            "nutritionist_completed",
            menu=recommendation.menu_name,
            calories=recommendation.estimated_calories,
        )

        return {
            "nutritionist_recommendation": recommendation,
            "events": [{
                "type": "progress",
                "node": "nutritionist",
                "status": "completed",
                "data": {
                    "menu": recommendation.menu_name,
                    "day": state.get("current_day"),
                    "meal": state.get("current_meal_index", 0) + 1,
                    "meal_type": state.get("current_meal_type"),
                }
            }],
        }

    except JSONDecodeError as e:
        # EC-020: Malformed JSON from LLM - return None for graceful retry
        logger.error(
            "nutritionist_json_decode_failed",
            error=str(e),
            response_preview=response[:200] if 'response' in locals() else "N/A"
        )
        return {
            "nutritionist_recommendation": None,
            "events": [{
                "type": "error",
                "node": "nutritionist",
                "status": "json_decode_failed",
                "data": {"error": "Invalid JSON from LLM"}
            }],
        }

    except ValidationError as e:
        # EC-020: Missing or invalid fields in LLM response
        missing_fields = [err["loc"][0] for err in e.errors() if err["type"] == "missing"]
        logger.error(
            "nutritionist_validation_failed",
            missing_fields=missing_fields,
            all_errors=e.errors(),
            response_preview=recommendation_data if 'recommendation_data' in locals() else "N/A"
        )
        return {
            "nutritionist_recommendation": None,
            "events": [{
                "type": "error",
                "node": "nutritionist",
                "status": "validation_failed",
                "data": {"missing_fields": missing_fields}
            }],
        }

    except Exception as e:
        # Unexpected errors still raise
        logger.error("nutritionist_failed", error=str(e))
        raise
