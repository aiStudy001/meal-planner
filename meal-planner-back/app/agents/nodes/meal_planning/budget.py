"""예산 관리 에이전트"""
import re
from json import JSONDecodeError

from pydantic import ValidationError

from app.models.state import MealPlanState, MealRecommendation
from app.services.llm_service import get_llm_service, parse_json_response
from app.services.ingredient_pricing import get_pricing_service
from app.utils.logging import get_logger
from app.utils.prompt_safety import escape_for_llm

logger = get_logger(__name__)


def _parse_amount_to_grams(amount_str: str) -> float:
    """재료 수량 문자열을 그램 단위로 변환

    Args:
        amount_str: "150g", "1kg", "100ml" 등의 문자열

    Returns:
        그램 단위 수량 (float)
    """
    # "150g" → 150.0
    match_g = re.search(r'(\d+(?:\.\d+)?)\s*g', amount_str, re.IGNORECASE)
    if match_g:
        return float(match_g.group(1))

    # "1kg" → 1000.0
    match_kg = re.search(r'(\d+(?:\.\d+)?)\s*kg', amount_str, re.IGNORECASE)
    if match_kg:
        return float(match_kg.group(1)) * 1000

    # "100ml" → 100.0 (밀도 1로 가정)
    match_ml = re.search(r'(\d+(?:\.\d+)?)\s*ml', amount_str, re.IGNORECASE)
    if match_ml:
        return float(match_ml.group(1))

    # 파싱 실패 시 기본값
    logger.warning("amount_parse_failed", amount_str=amount_str)
    return 100.0


async def budget_agent(state: MealPlanState) -> dict:
    """예산 관리 에이전트: 비용 효율 관점에서 메뉴 추천 (Tavily 가격 검색)

    Args:
        state: 현재 그래프 상태

    Returns:
        업데이트할 상태 dict
    """
    profile = state["profile"]
    targets = state["per_meal_targets"]
    current_meal_type = state["current_meal_type"]
    
    # 차등 배분 시 현재 끼니 타입에 맞는 예산 사용
    per_meal_budgets = state.get("per_meal_budgets")
    if per_meal_budgets and current_meal_type in per_meal_budgets:
        budget = per_meal_budgets[current_meal_type]
    else:
        budget = state["per_meal_budget"]

    # 이전 실패 이력 가져오기
    previous_failures = state.get("previous_validation_failures", [])
    retry_count = state.get("retry_count", 0)

    logger.info(
        "budget_started",
        meal_type=current_meal_type,
        day=state["current_day"],
        budget=budget,
        budget_source="per_meal_budgets" if per_meal_budgets else "per_meal_budget",
    )

    # Chef가 제공한 재료 가져오기
    chef_recommendation = state.get("chef_recommendation")
    ingredients = []
    if chef_recommendation:
        ingredients = chef_recommendation.ingredients or []
        logger.info("chef_ingredients_received", count=len(ingredients))

    # Tavily로 각 재료 가격 검색
    pricing_service = get_pricing_service()
    ingredient_prices = []
    total_estimated_cost = 0

    if ingredients:
        for ing in ingredients:
            ingredient_name = ing.get("name", "")
            amount_str = ing.get("amount", "100g")
            amount_g = _parse_amount_to_grams(amount_str)

            try:
                price_info = await pricing_service.get_ingredient_price(
                    ingredient_name=ingredient_name,
                    amount_g=amount_g
                )
                ingredient_prices.append(price_info)
                total_estimated_cost += price_info["total_price"]
                logger.debug(
                    "price_searched",
                    ingredient=ingredient_name,
                    amount_g=amount_g,
                    price=price_info["total_price"],
                    source=price_info["source"]
                )
            except Exception as e:
                logger.warning("price_search_failed", ingredient=ingredient_name, error=str(e))

        logger.info(
            "price_search_completed",
            total_ingredients=len(ingredients),
            successful_searches=len(ingredient_prices),
            total_cost=total_estimated_cost
        )

    # 가격 상세 정보 생성
    price_details = ""
    if ingredient_prices:
        price_details = "\n## 재료별 실시간 가격 (Tavily 검색 결과)\n"
        for p in ingredient_prices:
            source_display = {
                "tavily": "Tavily 검색",
                "cache": "캐시",
                "default": "기본값",
                "fallback": "폴백"
            }.get(p["source"], p["source"])

            price_details += f"- {p['name']} {p['amount_g']}g: {p['total_price']:,}원 "
            price_details += f"(그램당 {p['price_per_gram']:.2f}원, 출처: {source_display})\n"

        budget_diff = total_estimated_cost - budget
        price_details += f"\n## 현재 예상 총액\n"
        price_details += f"{total_estimated_cost:,}원 (예산 대비 {budget_diff:+,}원)\n"

    prompt = f"""당신은 가계부 전문가이자 요리 연구가입니다.

다음 조건에 맞는 {state["current_meal_type"]} 메뉴 1개를 추천해주세요.

## 예산 조건
- 1끼니 예산: {budget:,}원
- 가성비를 최우선으로 고려

## 영양 목표 (참고)
- 칼로리: {targets.calories:.0f}kcal
- 단백질: {targets.protein_g:.0f}g

## 제한 사항
- 제외 재료: {', '.join(escape_for_llm(r) for r in profile.restrictions) if profile.restrictions else '없음'}

{price_details}

예산 {budget:,}원 내에서 영양가 있는 메뉴를 추천해주세요.
{'필요시 재료를 조정하여 예산에 맞춰주세요.' if ingredient_prices else '저렴하면서도 영양가 높은 식재료를 활용하세요.'}"""

    # 피드백 섹션 생성 (참고용)
    feedback_section = ""
    if retry_count > 0 and previous_failures:
        feedback_section = "\n\n## 참고: 이전 메뉴 실패 이력\n"
        feedback_section += "영양사와 셰프의 추천이 다음 이유로 실패했습니다:\n"

        for failure in previous_failures[-3:]:  # 최근 3개만
            validator = failure.get("validator", "Unknown")
            issues = failure.get("issues", [])
            issue_text = issues[0] if issues else "N/A"
            feedback_section += f"- [{validator}] {issue_text}\n"

        logger.info(
            "retry_with_feedback",
            retry_count=retry_count,
            previous_failures_count=len(previous_failures),
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
    "reasoning": "추천 이유 (비용 효율 강조)"
}}

**필수 필드**: menu_name, ingredients, estimated_calories, estimated_cost, cooking_time_minutes, reasoning
"""

    llm_service = get_llm_service()
    try:
        response = await llm_service.ainvoke(prompt)
        logger.debug("budget_llm_response", response=response)
        recommendation_data = parse_json_response(response)
        logger.debug("budget_parsed_data", data=recommendation_data)

        # ingredient_prices 추가
        recommendation_data["ingredient_prices"] = ingredient_prices

        recommendation = MealRecommendation(**recommendation_data)

        logger.info(
            "budget_completed",
            menu=recommendation.menu_name,
            cost=recommendation.estimated_cost,
            price_search_count=len(ingredient_prices),
        )

        return {
            "budget_recommendation": recommendation,
            "events": [{
                "type": "progress",
                "node": "budget",
                "status": "completed",
                "data": {
                    "menu": recommendation.menu_name,
                    "price_search_count": len(ingredient_prices),
                    "total_estimated_cost": total_estimated_cost,
                    "day": state.get("current_day"),
                    "meal": state.get("current_meal_index", 0) + 1,
                    "meal_type": state.get("current_meal_type"),
                }
            }],
        }

    except JSONDecodeError as e:
        # EC-020: Malformed JSON from LLM - return None for graceful retry
        logger.error(
            "budget_json_decode_failed",
            error=str(e),
            response_preview=response[:200] if 'response' in locals() else "N/A"
        )
        return {
            "budget_recommendation": None,
            "events": [{
                "type": "error",
                "node": "budget",
                "status": "json_decode_failed",
                "data": {"error": "Invalid JSON from LLM"}
            }],
        }

    except ValidationError as e:
        # EC-020: Missing or invalid fields in LLM response
        missing_fields = [err["loc"][0] for err in e.errors() if err["type"] == "missing"]
        logger.error(
            "budget_validation_failed",
            missing_fields=missing_fields,
            all_errors=e.errors(),
            response_preview=recommendation_data if 'recommendation_data' in locals() else "N/A"
        )
        return {
            "budget_recommendation": None,
            "events": [{
                "type": "error",
                "node": "budget",
                "status": "validation_failed",
                "data": {"missing_fields": missing_fields}
            }],
        }

    except Exception as e:
        # Unexpected errors still raise
        logger.error("budget_failed", error=str(e))
        raise
