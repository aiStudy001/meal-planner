"""LLM 서비스 (Claude API + Mock 모드)"""
import asyncio
import json
import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """LLM 서비스 (Claude API Wrapper)"""

    def __init__(self, mock_mode: bool = False):
        """
        Args:
            mock_mode: True면 실제 API 호출 없이 더미 응답 반환
        """
        self.mock_mode = mock_mode

        if not mock_mode:
            # Use settings from Pydantic, not os.getenv()
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")

            self.llm = ChatAnthropic(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                api_key=settings.ANTHROPIC_API_KEY,
            )
            logger.info("llm_service_initialized", model=self.llm.model)
        else:
            self.llm = None
            logger.info("llm_service_initialized", mode="mock")

    async def ainvoke(self, prompt: str) -> str:
        """비동기 LLM 호출

        Args:
            prompt: 프롬프트 문자열

        Returns:
            LLM 응답 문자열

        Raises:
            TimeoutError: 25초 timeout 초과 시 (EC-018)
            Exception: API 호출 실패 시 (rate limit 3회 재시도 후 실패)
        """
        if self.mock_mode:
            return self._get_mock_response(prompt)

        # EC-019: Rate limit retry with exponential backoff
        max_retries = 3
        retry_delays = [1, 2, 4]  # seconds

        for attempt in range(max_retries + 1):
            try:
                # EC-018: Timeout wrapper (25s < FastAPI 30s default)
                async with asyncio.timeout(25):
                    messages = [HumanMessage(content=prompt)]
                    response = await self.llm.ainvoke(messages)
                    logger.info(
                        "llm_invoked",
                        prompt_length=len(prompt),
                        response_length=len(response.content),
                        attempt=attempt + 1
                    )
                    return response.content

            except asyncio.TimeoutError:
                logger.error(
                    "llm_timeout",
                    prompt_length=len(prompt),
                    timeout_seconds=25,
                    prompt_preview=prompt[:100]
                )
                raise TimeoutError(
                    f"LLM API 응답 시간이 초과되었습니다 (25초). "
                    f"프롬프트 길이: {len(prompt)}자"
                )

            except Exception as e:
                error_str = str(e).lower()

                # EC-019: Rate limit detection (429 or rate limit keywords)
                is_rate_limit = (
                    "429" in error_str or
                    "rate limit" in error_str or
                    "quota" in error_str or
                    "too many requests" in error_str
                )

                if is_rate_limit and attempt < max_retries:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "llm_rate_limit_retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        retry_delay_seconds=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
                    continue  # Retry

                # Not rate limit or max retries reached
                logger.error(
                    "llm_invocation_failed",
                    error=str(e),
                    attempt=attempt + 1,
                    is_rate_limit=is_rate_limit,
                    prompt_preview=prompt[:100]
                )
                raise

        # Should never reach here due to raise in loop
        raise RuntimeError("LLM invocation failed after all retries")

    def _get_mock_response(self, prompt: str) -> str:
        """Mock 응답 생성 (프롬프트 키워드 기반)"""
        # 노드 타입 감지 (구체적인 것부터 체크)
        if "총괄" in prompt or "conflict" in prompt.lower() or "3명의 전문가" in prompt:
            return self._mock_conflict_resolver_response()
        elif "영양 검증" in prompt or "nutrition_checker" in prompt.lower():
            return self._mock_nutrition_checker_response()
        elif "알레르기 검증" in prompt or "allergy_checker" in prompt.lower():
            return self._mock_allergy_checker_response()
        elif "조리시간 검증" in prompt or "time_checker" in prompt.lower():
            return self._mock_time_checker_response()
        elif "영양사" in prompt or "nutritionist" in prompt.lower():
            return self._mock_nutritionist_response()
        elif "셰프" in prompt or "chef" in prompt.lower():
            return self._mock_chef_response()
        elif "예산" in prompt or "budget" in prompt.lower():
            return self._mock_budget_response()
        else:
            return '{"menu_name": "테스트 메뉴", "ingredients": [{"name": "테스트 재료", "amount": "100g"}]}'

    def _mock_nutritionist_response(self) -> str:
        """영양사 Mock 응답"""
        return json.dumps({
            "menu_name": "닭가슴살 샐러드",
            "ingredients": [
                {"name": "닭가슴살", "amount": "150g"},
                {"name": "양상추", "amount": "100g"},
                {"name": "방울토마토", "amount": "80g"},
                {"name": "올리브유", "amount": "10ml"}
            ],
            "estimated_calories": 350,
            "estimated_cost": 5000,
            "cooking_time_minutes": 15,
            "reasoning": "고단백, 저칼로리 식단으로 다이어트에 적합합니다."
        }, ensure_ascii=False)

    def _mock_chef_response(self) -> str:
        """셰프 Mock 응답"""
        return json.dumps({
            "menu_name": "간단한 볶음밥",
            "ingredients": [
                {"name": "밥", "amount": "210g"},
                {"name": "계란", "amount": "2개"},
                {"name": "햄", "amount": "50g"},
                {"name": "야채", "amount": "100g"}
            ],
            "estimated_calories": 450,
            "estimated_cost": 3000,
            "cooking_time_minutes": 10,
            "reasoning": "초급자도 쉽게 만들 수 있는 간단한 요리입니다."
        }, ensure_ascii=False)

    def _mock_budget_response(self) -> str:
        """예산 전문가 Mock 응답"""
        return json.dumps({
            "menu_name": "계란김치볶음밥",
            "ingredients": [
                {"name": "밥", "amount": "210g"},
                {"name": "계란", "amount": "2개"},
                {"name": "김치", "amount": "100g"},
                {"name": "참기름", "amount": "5ml"}
            ],
            "estimated_calories": 420,
            "estimated_cost": 2000,
            "cooking_time_minutes": 10,
            "reasoning": "가성비가 매우 뛰어난 한끼 식사입니다."
        }, ensure_ascii=False)

    def _mock_conflict_resolver_response(self) -> str:
        """Conflict Resolver Mock 응답 (검증 통과 가능한 영양소)"""
        return json.dumps({
            "menu_name": "닭가슴살 볶음밥",
            "ingredients": [
                {"name": "밥", "amount": "210g"},
                {"name": "닭가슴살", "amount": "100g"},
                {"name": "계란", "amount": "1개"},
                {"name": "야채", "amount": "100g"}
            ],
            "calories": 550,
            "carb_g": 65,
            "protein_g": 35,
            "fat_g": 18,
            "sodium_mg": 500,
            "sugar_g": 5,
            "cooking_time_minutes": 15,
            "estimated_cost": 4000,
            "recipe_steps": [
                "1. 닭가슴살을 먹기 좋은 크기로 자릅니다.",
                "2. 팬에 기름을 두르고 닭가슴살을 볶습니다.",
                "3. 야채를 추가하여 함께 볶습니다.",
                "4. 밥과 계란을 넣고 볶습니다.",
                "5. 간을 맞추고 완성합니다."
            ]
        }, ensure_ascii=False)

    def _mock_nutrition_checker_response(self) -> str:
        """영양 검증기 Mock 응답 (통과)"""
        return json.dumps({
            "passed": True,
            "reason": "칼로리와 매크로 영양소가 목표 범위 내에 있습니다.",
            "details": {
                "calorie_diff_percent": 5.2,
                "within_tolerance": True
            }
        }, ensure_ascii=False)

    def _mock_allergy_checker_response(self) -> str:
        """알레르기 검증기 Mock 응답 (통과)"""
        return json.dumps({
            "passed": True,
            "reason": "알레르기 성분이 포함되지 않았습니다.",
            "details": {
                "checked_ingredients": ["닭가슴살", "밥", "계란", "야채"],
                "allergens_found": []
            }
        }, ensure_ascii=False)

    def _mock_time_checker_response(self) -> str:
        """조리시간 검증기 Mock 응답 (통과)"""
        return json.dumps({
            "passed": True,
            "reason": "조리 시간이 제한 시간 내에 있습니다.",
            "details": {
                "cooking_time": 15,
                "time_limit": 30,
                "within_limit": True
            }
        }, ensure_ascii=False)


def parse_json_response(response: str) -> dict[str, Any]:
    """LLM 응답에서 JSON 파싱

    Args:
        response: LLM 응답 문자열

    Returns:
        파싱된 JSON dict

    Raises:
        json.JSONDecodeError: JSON 파싱 실패 시
    """
    try:
        # 코드 블록 제거 (```json ... ``` 형식)
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        # JSON 숫자에서 쉼표 제거 (예: 7,200 → 7200)
        import re
        # 숫자 내부의 쉼표 제거 (따옴표 밖에 있는 경우만)
        response = re.sub(r'(?<=\")\s*(\d{1,3}(?:,\d{3})+)\s*(?=\"|,|})',
                          lambda m: m.group(1).replace(',', ''), response)
        # 숫자 값에서 쉼표 제거 (: 7,200 형식)
        response = re.sub(r':\s*(\d{1,3}(?:,\d{3})+)',
                          lambda m: ': ' + m.group(1).replace(',', ''), response)

        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.error("json_parse_failed", error=str(e), full_response=response)
        raise


# 싱글톤 인스턴스
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """LLM Service 싱글톤 가져오기"""
    global _llm_service
    if _llm_service is None:
        mock_mode = settings.MOCK_MODE
        _llm_service = LLMService(mock_mode=mock_mode)
    return _llm_service
