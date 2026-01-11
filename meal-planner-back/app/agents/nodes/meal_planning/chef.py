"""셰프 에이전트"""
from json import JSONDecodeError

from pydantic import ValidationError

from app.models.state import MealPlanState, MealRecommendation
from app.services.llm_service import get_llm_service, parse_json_response
from app.services.recipe_search import get_recipe_search_service
from app.utils.constants import COOKING_TIME_LIMITS, ENABLE_RECIPE_SEARCH
from app.utils.logging import get_logger
from app.utils.prompt_safety import escape_for_llm

logger = get_logger(__name__)


async def chef_agent(state: MealPlanState) -> dict:
    """셰프 에이전트: 맛과 조리 용이성 관점에서 메뉴 추천

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    profile = state["profile"]
    targets = state["per_meal_targets"]
    time_limit = COOKING_TIME_LIMITS[profile.cooking_time]

    # 이전 실패 이력 가져오기
    previous_failures = state.get("previous_validation_failures", [])
    retry_count = state.get("retry_count", 0)

    logger.info(
        "chef_started",
        meal_type=state["current_meal_type"],
        day=state["current_day"],
        time_limit=time_limit,
        skill_level=profile.skill_level,
    )

    # Recipe search enhancement
    recipe_context = ""
    if ENABLE_RECIPE_SEARCH:
        search_service = get_recipe_search_service()
        try:
            search_query = f"{state['current_meal_type']} {profile.skill_level} {time_limit}분"
            if profile.restrictions:
                search_query += f" exclude:{','.join(profile.restrictions[:2])}"

            recipes = await search_service.search_recipes(
                query=search_query,
                filters={
                    "max_cooking_time": time_limit,
                    "difficulty": profile.skill_level,
                    "exclude_ingredients": profile.restrictions,
                    "target_calories": targets.calories,
                    "calorie_tolerance": 0.3,
                },
            )

            if recipes:
                recipe_context = "\n## 참고 레시피 (실제 데이터)\n"
                for i, recipe in enumerate(recipes[:3], 1):
                    recipe_context += f"\n### 레시피 {i}: {recipe['name']}\n"
                    recipe_context += f"- 조리시간: {recipe.get('cooking_time', 'N/A')}분\n"
                    recipe_context += f"- 칼로리: {recipe.get('calories', 'N/A')}kcal\n"
                    recipe_context += f"- 난이도: {recipe.get('difficulty', 'N/A')}\n"
                    recipe_context += f"- 재료: {', '.join(recipe.get('ingredients', [])[:5])}\n"

                logger.info("recipe_search_success", count=len(recipes))
        except Exception as e:
            logger.warning("recipe_search_failed", error=str(e))

    # 중복 방지: 이미 완료된 메뉴 목록 추출
    completed_meals = state.get("completed_meals", [])
    recently_used_recipes = [meal.menu_name for meal in completed_meals[-5:]] if completed_meals else []

    # 중복 방지 섹션 생성
    duplicate_prevention = ""
    if recently_used_recipes:
        duplicate_prevention = f"""
## ⚠️ 중복 방지
최근 사용된 메뉴: {', '.join(recently_used_recipes)}
**중요**: 위 메뉴들과 완전히 다른 새로운 메뉴를 추천해주세요. 주재료와 조리법을 다르게 해주세요.
"""

    prompt = f"""당신은 전문 셰프입니다.

다음 조건에 맞는 {state["current_meal_type"]} 메뉴 1개를 추천해주세요.

## 조리 조건
- 조리 시간: {time_limit}분 이내
- 요리 실력: {profile.skill_level}
- 제외 재료: {', '.join(escape_for_llm(r) for r in profile.restrictions) if profile.restrictions else '없음'}
{duplicate_prevention}
## 영양 목표 (참고)
- 칼로리: {targets.calories:.0f}kcal
- 단백질: {targets.protein_g:.0f}g

{recipe_context}

## 요리 실력별 가이드
- 초급: 전자레인지, 끓이기, 간단한 볶음만 가능
- 중급: 볶음, 굽기, 찜 가능
- 고급: 복합 조리, 베이킹, 다양한 기법 가능

맛있고 조리하기 쉬운 메뉴를 추천해주세요.
{recipe_context and "위 참고 레시피를 활용하거나 변형할 수 있습니다." or ""}"""

    # 피드백 섹션 생성
    feedback_section = ""
    if retry_count > 0 and previous_failures:
        # 셰프 관련 실패 (allergy, time)
        chef_failures = [
            f for f in previous_failures
            if f.get("validator") in ["allergy_checker", "time_checker"]
            and f.get("retry_count") == retry_count - 1
        ]

        if chef_failures:
            feedback_section = "\n\n## ⚠️ 이전 시도 피드백\n"
            feedback_section += f"**재시도 {retry_count}회차**: 이전 메뉴가 다음 이유로 실패했습니다.\n\n"

            for failure in chef_failures:
                feedback_section += f"### 메뉴: {failure.get('menu_name', 'Unknown')}\n"
                for issue in failure.get("issues", []):
                    feedback_section += f"- {issue}\n"
                feedback_section += "\n"

            feedback_section += "**중요**: 위 문제를 해결하도록 재료나 조리법을 변경해주세요.\n"

            logger.info(
                "retry_with_feedback",
                retry_count=retry_count,
                previous_failures_count=len(previous_failures),
                chef_failures_count=len(chef_failures),
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
        logger.debug("chef_llm_response", response=response)
        recommendation_data = parse_json_response(response)
        logger.debug("chef_parsed_data", data=recommendation_data)
        recommendation = MealRecommendation(**recommendation_data)

        logger.info(
            "chef_completed",
            menu=recommendation.menu_name,
            cooking_time=recommendation.cooking_time_minutes,
        )

        return {
            "chef_recommendation": recommendation,
            "events": [{
                "type": "progress",
                "node": "chef",
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
            "chef_json_decode_failed",
            error=str(e),
            response_preview=response[:200] if 'response' in locals() else "N/A"
        )
        return {
            "chef_recommendation": None,
            "events": [{
                "type": "error",
                "node": "chef",
                "status": "json_decode_failed",
                "data": {"error": "Invalid JSON from LLM"}
            }],
        }

    except ValidationError as e:
        # EC-020: Missing or invalid fields in LLM response
        missing_fields = [err["loc"][0] for err in e.errors() if err["type"] == "missing"]
        logger.error(
            "chef_validation_failed",
            missing_fields=missing_fields,
            all_errors=e.errors(),
            response_preview=recommendation_data if 'recommendation_data' in locals() else "N/A"
        )
        return {
            "chef_recommendation": None,
            "events": [{
                "type": "error",
                "node": "chef",
                "status": "validation_failed",
                "data": {"missing_fields": missing_fields}
            }],
        }

    except Exception as e:
        # Unexpected errors still raise
        logger.error("chef_failed", error=str(e))
        raise
