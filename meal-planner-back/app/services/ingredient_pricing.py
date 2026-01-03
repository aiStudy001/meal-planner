"""재료 가격 검색 서비스 (Tavily + 캐싱)"""
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from tavily import TavilyClient

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class IngredientPricingService:
    """재료 가격 검색 서비스 (Tavily + 캐싱)

    폴백 체인:
    1. 캐시 확인 (일일 파일 기반)
    2. Tavily API 검색
    3. 기본 가격 맵 (default_ingredient_prices.json)
    4. 하드코딩 평균값 (20원/g)
    """

    def __init__(self, cache_dir: str | None = None):
        """초기화

        Args:
            cache_dir: 캐시 디렉토리 경로 (None이면 settings.PRICE_CACHE_DIR 사용)
        """
        # Tavily Client 초기화 (TAVILY_API_KEY가 있을 때만)
        self.tavily = None
        if settings.TAVILY_API_KEY:
            try:
                self.tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
                logger.info("tavily_client_initialized")
            except Exception as e:
                logger.warning("tavily_initialization_failed", error=str(e))

        # 캐시 디렉토리 설정
        self.cache_dir = Path(cache_dir or settings.PRICE_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 기본 가격 맵 로드
        self.default_prices = self._load_default_prices()

    def _load_default_prices(self) -> dict[str, dict[str, Any]]:
        """기본 가격 맵 로드"""
        try:
            prices_file = Path("data/default_ingredient_prices.json")
            if prices_file.exists():
                with open(prices_file, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning("default_prices_load_failed", error=str(e))

        return {}

    async def get_ingredient_price(
        self,
        ingredient_name: str,
        amount_g: float
    ) -> dict[str, Any]:
        """재료 가격 조회 (캐시 → Tavily → 기본값 → 폴백)

        Args:
            ingredient_name: 재료명 (예: "닭가슴살")
            amount_g: 그램 수량 (예: 150.0)

        Returns:
            {
                "name": "닭가슴살",
                "amount_g": 150.0,
                "price_per_gram": 0.035,
                "total_price": 5250,
                "source": "tavily|cache|default|fallback",
                "source_url": "https://..."  # Tavily만 해당
            }
        """
        # 1. 캐시 확인
        cached = self._load_from_cache(ingredient_name)
        if cached:
            logger.info("price_from_cache", ingredient=ingredient_name)
            return self._calculate_price(cached, ingredient_name, amount_g, "cache")

        # 2. Tavily 검색
        if self.tavily:
            try:
                tavily_result = await self._search_tavily(ingredient_name)
                self._save_to_cache(ingredient_name, tavily_result)
                logger.info("price_from_tavily", ingredient=ingredient_name)
                return self._calculate_price(tavily_result, ingredient_name, amount_g, "tavily")
            except Exception as e:
                logger.warning("tavily_search_failed", ingredient=ingredient_name, error=str(e))

        # 3. 기본값 폴백
        default = self.default_prices.get(ingredient_name)
        if default:
            logger.info("price_from_default", ingredient=ingredient_name)
            return self._calculate_price(default, ingredient_name, amount_g, "default")

        # 4. 완전 실패 시 평균값
        logger.warning("price_fallback_used", ingredient=ingredient_name)
        return {
            "name": ingredient_name,
            "amount_g": amount_g,
            "price_per_gram": 0.02,  # 기본 20원/g
            "total_price": int(amount_g * 0.02),
            "source": "fallback",
            "source_url": None
        }

    async def _search_tavily(self, ingredient_name: str) -> dict[str, Any]:
        """Tavily로 재료 가격 검색

        Args:
            ingredient_name: 재료명

        Returns:
            {
                "price_per_gram": 0.035,
                "source_url": "https://...",
                "search_date": "2026-01-02"
            }

        Raises:
            ValueError: 검색 결과가 없을 때
        """
        query = f"{ingredient_name} 가격 그램당 100g 마트"

        logger.info("tavily_searching", ingredient=ingredient_name, query=query)

        results = self.tavily.search(
            query=query,
            search_depth="basic",
            max_results=3
        )

        # 첫 결과에서 가격 추출
        if results and results.get("results"):
            first_result = results["results"][0]
            content = first_result.get("content", "")
            url = first_result.get("url", "")

            # 가격 파싱 (예: "100g당 3,500원")
            price_per_gram = self._extract_price(content, ingredient_name)

            return {
                "price_per_gram": price_per_gram,
                "source_url": url,
                "search_date": str(date.today())
            }

        raise ValueError(f"No Tavily results found for {ingredient_name}")

    def _extract_price(self, content: str, ingredient_name: str) -> float:
        """텍스트에서 가격 추출

        지원 형식:
        - "100g당 3,500원"
        - "1kg 35,000원"
        - "닭가슴살 150g 5,400원"

        Args:
            content: 검색 결과 텍스트
            ingredient_name: 재료명 (폴백용)

        Returns:
            그램당 가격 (float)
        """
        # 패턴 1: "100g당 3,500원"
        pattern1 = r'(\d+)g당?\s*(\d{1,3}(?:,\d{3})*)\s*원'
        match1 = re.search(pattern1, content)
        if match1:
            grams = int(match1.group(1))
            price = int(match1.group(2).replace(',', ''))
            logger.info("price_extracted_pattern1", grams=grams, price=price)
            return price / grams

        # 패턴 2: "1kg 35,000원"
        pattern2 = r'(\d+)\s*kg\s*(\d{1,3}(?:,\d{3})*)\s*원'
        match2 = re.search(pattern2, content)
        if match2:
            kg = int(match2.group(1))
            price = int(match2.group(2).replace(',', ''))
            logger.info("price_extracted_pattern2", kg=kg, price=price)
            return price / (kg * 1000)

        # 패턴 3: "재료명 100g 3,500원"
        pattern3 = rf'{ingredient_name}\s*(\d+)g\s*(\d{{1,3}}(?:,\d{{3}})*)\s*원'
        match3 = re.search(pattern3, content)
        if match3:
            grams = int(match3.group(1))
            price = int(match3.group(2).replace(',', ''))
            logger.info("price_extracted_pattern3", grams=grams, price=price)
            return price / grams

        # 기본값 반환
        logger.warning("price_extraction_failed", content_preview=content[:100])
        default = self.default_prices.get(ingredient_name, {})
        return default.get("price_per_gram", 0.02)

    def _load_from_cache(self, ingredient_name: str) -> dict[str, Any] | None:
        """오늘 날짜 캐시 로드

        Args:
            ingredient_name: 재료명

        Returns:
            캐시된 가격 정보 또는 None
        """
        cache_file = self.cache_dir / f"prices_{date.today()}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, encoding="utf-8") as f:
                cache = json.load(f)
            return cache.get(ingredient_name)
        except Exception as e:
            logger.warning("cache_load_failed", error=str(e))
            return None

    def _save_to_cache(self, ingredient_name: str, data: dict[str, Any]):
        """오늘 날짜 캐시 저장

        Args:
            ingredient_name: 재료명
            data: 가격 정보
        """
        cache_file = self.cache_dir / f"prices_{date.today()}.json"

        # 기존 캐시 로드
        cache = {}
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cache = json.load(f)
            except Exception as e:
                logger.warning("cache_load_for_save_failed", error=str(e))

        # 새 데이터 추가
        cache[ingredient_name] = data

        # 저장
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            logger.info("price_cached", ingredient=ingredient_name)
        except Exception as e:
            logger.error("cache_save_failed", error=str(e))

    def _calculate_price(
        self,
        data: dict[str, Any],
        ingredient_name: str,
        amount_g: float,
        source: str
    ) -> dict[str, Any]:
        """최종 가격 계산

        Args:
            data: 가격 정보 (price_per_gram 포함)
            ingredient_name: 재료명
            amount_g: 그램 수량
            source: 출처 ("tavily", "cache", "default")

        Returns:
            계산된 가격 정보
        """
        price_per_gram = data["price_per_gram"]
        total_price = int(amount_g * price_per_gram)

        return {
            "name": ingredient_name,
            "amount_g": amount_g,
            "price_per_gram": price_per_gram,
            "total_price": total_price,
            "source": source,
            "source_url": data.get("source_url")
        }


# 싱글톤
_pricing_service: IngredientPricingService | None = None


def get_pricing_service() -> IngredientPricingService:
    """IngredientPricingService 싱글톤 가져오기

    Returns:
        IngredientPricingService 인스턴스
    """
    global _pricing_service
    if _pricing_service is None:
        _pricing_service = IngredientPricingService()
    return _pricing_service
