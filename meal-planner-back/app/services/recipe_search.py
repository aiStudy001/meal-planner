"""레시피 검색 서비스 (Tavily + CSV Fallback)"""
import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd

from app.utils.constants import RECIPE_CACHE_TTL_SECONDS, RECIPE_SEARCH_LIMIT
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RecipeSearchService:
    """레시피 검색 서비스 (Tavily API + 로컬 CSV Fallback)"""

    def __init__(
        self,
        mock_mode: bool = False,
        tavily_api_key: Optional[str] = None,
        csv_path: str = "data/recipes_with_nutrition.csv",
        enable_web_search: bool = True,
    ):
        """
        Args:
            mock_mode: True면 mock 데이터 반환
            tavily_api_key: Tavily API 키 (웹 검색용)
            csv_path: 로컬 CSV 파일 경로
            enable_web_search: 웹 검색 활성화 여부
        """
        self.mock_mode = mock_mode
        self.csv_path = csv_path
        self.enable_web_search = enable_web_search

        # Tavily client 초기화
        self.tavily_client = None
        if not mock_mode and enable_web_search and tavily_api_key:
            try:
                from tavily import TavilyClient

                self.tavily_client = TavilyClient(api_key=tavily_api_key)
                logger.info("tavily_client_initialized")
            except ImportError:
                logger.warning("tavily_import_failed", msg="tavily-python not installed")
            except Exception as e:
                logger.warning("tavily_init_failed", error=str(e))

        # CSV DataFrame 캐시 (lazy loading)
        self._csv_df: Optional[pd.DataFrame] = None

        # 검색 결과 캐시 {cache_key: (results, expiry_time)}
        self._cache: dict[str, tuple[list[dict], datetime]] = {}

        logger.info(
            "recipe_search_service_initialized",
            mock_mode=mock_mode,
            enable_web_search=enable_web_search,
            csv_path=csv_path,
        )

    async def search_recipes(
        self, query: str, filters: Optional[dict] = None, limit: int = RECIPE_SEARCH_LIMIT
    ) -> list[dict]:
        """레시피 검색 (Fallback chain: Cache → Mock → Tavily → CSV)

        Args:
            query: 검색 쿼리 (예: "아침 초급 30분")
            filters: 필터 조건
                - max_cooking_time: int (조리 시간 제한, 분)
                - difficulty: str (난이도: 초급/중급/고급)
                - exclude_ingredients: list[str] (제외 재료)
                - target_calories: float (목표 칼로리)
                - calorie_tolerance: float (칼로리 허용 범위, 0.3 = ±30%)
            limit: 최대 결과 수

        Returns:
            레시피 리스트 [{
                "name": "메뉴명",
                "cooking_time": 15,
                "calories": 500,
                "difficulty": "초급",
                "ingredients": ["재료1", "재료2", ...],
                "category": "한식",
            }]
        """
        filters = filters or {}

        # 1. Cache check
        cache_key = self._generate_cache_key(query, filters, limit)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            logger.info("recipe_search_cache_hit", query=query)
            return cached

        # 2. Mock mode
        if self.mock_mode:
            results = self._get_mock_results(query, filters, limit)
            self._save_to_cache(cache_key, results)
            return results

        # 3. Tavily web search
        if self.enable_web_search and self.tavily_client:
            try:
                results = await self._search_tavily(query, filters, limit)
                if results:
                    self._save_to_cache(cache_key, results)
                    logger.info("recipe_search_tavily_success", query=query, count=len(results))
                    return results
            except Exception as e:
                logger.warning("tavily_search_failed", error=str(e), query=query)

        # 4. CSV fallback
        try:
            results = await self._search_local_csv(query, filters, limit)
            self._save_to_cache(cache_key, results)
            if results:
                logger.info("recipe_search_csv_success", query=query, count=len(results))
            else:
                logger.warning("recipe_search_no_results", query=query)
            return results
        except Exception as e:
            logger.warning("csv_search_failed", error=str(e), query=query, csv_path=self.csv_path)
            return []

    async def _search_tavily(self, query: str, filters: dict, limit: int) -> list[dict]:
        """Tavily API로 웹 검색"""
        if not self.tavily_client:
            return []

        # 검색 쿼리 강화
        enhanced_query = f"한국 레시피 {query}"

        # Tavily 검색 실행 (블로킹 호출을 async로 변환)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.tavily_client.search(
                query=enhanced_query,
                max_results=limit * 2,  # 필터링 후 부족할 수 있으므로 2배
                search_depth="basic",
                include_domains=["10000recipe.com", "wtable.co.kr", "haemukja.com"],
            ),
        )

        # 결과 파싱 및 정규화
        results = []
        for item in response.get("results", [])[:limit]:
            try:
                # 웹 검색 결과에서 레시피 정보 추출 (제한적)
                recipe = {
                    "name": item.get("title", "Unknown"),
                    "cooking_time": None,  # 웹에서 추출 어려움
                    "calories": None,
                    "difficulty": None,
                    "ingredients": [],
                    "category": "기타",
                    "source": "web",
                    "url": item.get("url"),
                }
                results.append(recipe)
            except Exception as e:
                logger.warning("tavily_result_parse_failed", error=str(e), item=item)

        return results

    async def _search_local_csv(self, query: str, filters: dict, limit: int) -> list[dict]:
        """로컬 CSV에서 레시피 검색 (pandas)"""
        # Lazy load CSV
        if self._csv_df is None:
            loop = asyncio.get_event_loop()
            try:
                self._csv_df = await loop.run_in_executor(
                    None, lambda: pd.read_csv(self.csv_path, encoding="utf-8")
                )
                logger.info("csv_loaded", rows=len(self._csv_df), path=self.csv_path)
            except Exception as e:
                logger.error("csv_load_failed", error=str(e), path=self.csv_path)
                raise

        df = self._csv_df.copy()

        # 필터 적용
        max_cooking_time = filters.get("max_cooking_time")
        if max_cooking_time:
            df = df[df["cooking_time"] <= max_cooking_time]

        difficulty = filters.get("difficulty")
        if difficulty:
            # 난이도 매핑: 초급 → 아무나, 중급 → 초급, 고급 → 중급
            difficulty_map = {"초급": ["아무나"], "중급": ["아무나", "초급"], "고급": ["아무나", "초급", "중급"]}
            allowed_difficulties = difficulty_map.get(difficulty, ["아무나", "초급", "중급"])
            df = df[df["difficulty"].isin(allowed_difficulties)]

        target_calories = filters.get("target_calories")
        calorie_tolerance = filters.get("calorie_tolerance", 0.3)
        if target_calories:
            min_cal = target_calories * (1 - calorie_tolerance)
            max_cal = target_calories * (1 + calorie_tolerance)
            df = df[(df["calories"] >= min_cal) & (df["calories"] <= max_cal)]

        # 제외 재료 필터링
        exclude_ingredients = filters.get("exclude_ingredients", [])
        if exclude_ingredients:
            for ingredient in exclude_ingredients:
                # ingredients_raw에 해당 재료가 포함되지 않은 레시피만
                df = df[~df["ingredients_raw"].str.contains(ingredient, case=False, na=False)]

        # 키워드 검색 (name, category, main_ingredient)
        if query:
            keywords = query.split()
            mask = pd.Series([False] * len(df), index=df.index)
            for keyword in keywords:
                mask |= (
                    df["name"].str.contains(keyword, case=False, na=False)
                    | df["category"].str.contains(keyword, case=False, na=False)
                    | df["main_ingredient"].str.contains(keyword, case=False, na=False)
                )
            df = df[mask]

        # 상위 N개 결과
        df = df.head(limit)

        # 결과 변환
        results = []
        for _, row in df.iterrows():
            try:
                # ingredients_parsed 파싱 (JSON 형식 예상)
                ingredients_list = []
                if pd.notna(row["ingredients_parsed"]):
                    try:
                        parsed = json.loads(row["ingredients_parsed"])
                        if isinstance(parsed, list):
                            ingredients_list = [
                                item["name"] if isinstance(item, dict) else str(item) for item in parsed
                            ]
                    except (json.JSONDecodeError, TypeError):
                        # 파싱 실패 시 raw 사용
                        if pd.notna(row["ingredients_raw"]):
                            ingredients_list = [
                                s.strip() for s in str(row["ingredients_raw"]).split(",")[:10]
                            ]

                recipe = {
                    "name": row["name"],
                    "cooking_time": int(row["cooking_time"]) if pd.notna(row["cooking_time"]) else None,
                    "calories": float(row["calories"]) if pd.notna(row["calories"]) else None,
                    "difficulty": row["difficulty"] if pd.notna(row["difficulty"]) else None,
                    "ingredients": ingredients_list,
                    "category": row["category"] if pd.notna(row["category"]) else "기타",
                    "carb_g": float(row["carb_g"]) if pd.notna(row["carb_g"]) else None,
                    "protein_g": float(row["protein_g"]) if pd.notna(row["protein_g"]) else None,
                    "fat_g": float(row["fat_g"]) if pd.notna(row["fat_g"]) else None,
                    "source": "csv",
                }
                results.append(recipe)
            except Exception as e:
                logger.warning("csv_row_parse_failed", error=str(e), row_index=row.name)

        return results

    def _get_mock_results(self, query: str, filters: dict, limit: int) -> list[dict]:
        """Mock 모드 레시피 데이터"""
        mock_recipes = [
            {
                "name": "닭가슴살 샐러드",
                "cooking_time": 15,
                "calories": 350,
                "difficulty": "초급",
                "ingredients": ["닭가슴살", "양상추", "방울토마토", "올리브유"],
                "category": "샐러드",
                "carb_g": 15,
                "protein_g": 40,
                "fat_g": 12,
                "source": "mock",
            },
            {
                "name": "계란김치볶음밥",
                "cooking_time": 10,
                "calories": 420,
                "difficulty": "초급",
                "ingredients": ["밥", "계란", "김치", "참기름"],
                "category": "밥",
                "carb_g": 65,
                "protein_g": 15,
                "fat_g": 12,
                "source": "mock",
            },
            {
                "name": "토마토 계란볶음",
                "cooking_time": 12,
                "calories": 280,
                "difficulty": "초급",
                "ingredients": ["토마토", "계란", "파", "식용유"],
                "category": "볶음",
                "carb_g": 18,
                "protein_g": 14,
                "fat_g": 16,
                "source": "mock",
            },
        ]

        # 필터 적용 (간단한 버전)
        filtered = mock_recipes.copy()

        max_cooking_time = filters.get("max_cooking_time")
        if max_cooking_time:
            filtered = [r for r in filtered if r["cooking_time"] <= max_cooking_time]

        difficulty = filters.get("difficulty")
        if difficulty:
            filtered = [r for r in filtered if r["difficulty"] == difficulty]

        return filtered[:limit]

    def _generate_cache_key(self, query: str, filters: dict, limit: int) -> str:
        """캐시 키 생성 (MD5 hash)"""
        cache_data = {"query": query, "filters": filters, "limit": limit}
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[list[dict]]:
        """캐시에서 결과 가져오기"""
        if cache_key in self._cache:
            results, expiry = self._cache[cache_key]
            if datetime.now() < expiry:
                return results
            else:
                # 만료된 캐시 삭제
                del self._cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, results: list[dict]) -> None:
        """캐시에 결과 저장"""
        expiry = datetime.now() + timedelta(seconds=RECIPE_CACHE_TTL_SECONDS)
        self._cache[cache_key] = (results, expiry)


# 싱글톤 인스턴스
_recipe_search_service: Optional[RecipeSearchService] = None


def get_recipe_search_service() -> RecipeSearchService:
    """Recipe Search Service 싱글톤 가져오기"""
    global _recipe_search_service
    if _recipe_search_service is None:
        mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        csv_path = os.getenv("RECIPES_CSV_PATH", "data/recipes_with_nutrition.csv")
        enable_web_search = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"

        _recipe_search_service = RecipeSearchService(
            mock_mode=mock_mode,
            tavily_api_key=tavily_api_key,
            csv_path=csv_path,
            enable_web_search=enable_web_search,
        )
    return _recipe_search_service
