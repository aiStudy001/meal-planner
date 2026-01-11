"""
대체 레시피 검색 서비스

기존 메뉴와 유사한 칼로리/비용의 대체 레시피 검색
"""

import asyncio
from typing import List, Dict, Optional
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AlternativeRecipeSearchService:
    """대체 레시피 검색 서비스"""

    def __init__(self, tavily_api_key: Optional[str] = None):
        """
        Args:
            tavily_api_key: Tavily API 키
        """
        self.tavily_client = None

        # Tavily 클라이언트 초기화
        if tavily_api_key:
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=tavily_api_key)
                logger.info("tavily_client_initialized_for_alternatives")
            except ImportError as e:
                logger.error("tavily_import_failed", error=str(e))
                raise ImportError(
                    "tavily-python package not installed. "
                    "Run: pip install tavily-python==0.7.17"
                ) from e
            except Exception as e:
                logger.error("tavily_init_failed", error=str(e))
                raise
        else:
            logger.warning(
                "tavily_api_key_not_configured",
                msg="TAVILY_API_KEY not set in .env - alternative recipe search will not work"
            )

    def build_search_query(
        self,
        base_menu: str,
        target_calories: int,
        restrictions: List[str]
    ) -> str:
        """
        대체 레시피 검색 쿼리 생성

        Args:
            base_menu: 현재 메뉴 이름
            target_calories: 목표 칼로리
            restrictions: 제외 재료

        Returns:
            검색 쿼리 문자열
        """
        # 기본 쿼리
        query_parts = [f"{base_menu}와 비슷한 레시피"]

        # 칼로리 조건
        query_parts.append(f"{target_calories}kcal")

        # 제외 재료
        if restrictions:
            exclude_str = " ".join([f"-{r}" for r in restrictions[:3]])  # 최대 3개만
            query_parts.append(exclude_str)

        query = " ".join(query_parts)
        logger.info("search_query_built", query=query)
        return query

    async def search_with_tavily(
        self,
        query: str,
        max_results: int = 15
    ) -> List[dict]:
        """
        Tavily API로 레시피 검색

        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        if not self.tavily_client:
            logger.warning("tavily_client_not_available")
            return []

        try:
            # 비동기 실행 (Tavily는 동기 API)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.tavily_client.search(
                    query=f"한국 레시피 {query}",
                    max_results=max_results,
                    search_depth="basic",
                    include_domains=["10000recipe.com", "wtable.co.kr", "haemukja.com"]
                )
            )

            results = response.get("results", [])
            logger.info(
                "tavily_search_completed",
                query=query,
                result_count=len(results)
            )
            return results

        except Exception as e:
            logger.error(
                "tavily_search_failed",
                error=str(e),
                query=query
            )
            return []

    def parse_recipe_from_search_result(
        self,
        result: dict
    ) -> Optional[Dict]:
        """
        Tavily 검색 결과에서 레시피 정보 추출

        Args:
            result: Tavily 검색 결과 단일 항목

        Returns:
            파싱된 레시피 딕셔너리 또는 None
        """
        try:
            # Tavily result 구조: {"title": str, "content": str, "url": str, "score": float}
            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")

            # 간단한 레시피 파싱 (실제로는 LLM이 파싱하거나 더 정교한 로직 필요)
            # 여기서는 제목을 메뉴 이름으로 사용
            recipe = {
                "name": title.split("-")[0].strip() if "-" in title else title[:30],
                "url": url,
                "content_preview": content[:200],
                # 실제로는 content에서 추출해야 하지만, 일단 기본값
                "calories": None,  # LLM으로 파싱 필요
                "cost": None,  # LLM으로 파싱 필요
                "cooking_time": None,  # LLM으로 파싱 필요
                "difficulty": "중급",  # 기본값
                "ingredients": []  # content에서 파싱 필요
            }

            return recipe

        except Exception as e:
            logger.warning(
                "recipe_parse_failed",
                error=str(e),
                result_title=result.get("title", "")
            )
            return None

    def is_within_tolerance(
        self,
        recipe: Dict,
        target_calories: int,
        target_cost: int,
        calorie_tolerance: int,
        cost_tolerance: int
    ) -> bool:
        """
        레시피가 허용 범위 내인지 확인

        Args:
            recipe: 레시피 딕셔너리
            target_calories: 목표 칼로리
            target_cost: 목표 비용
            calorie_tolerance: 칼로리 허용 범위 (±kcal)
            cost_tolerance: 비용 허용 범위 (±원)

        Returns:
            허용 범위 내 여부
        """
        calories = recipe.get("calories")
        cost = recipe.get("cost")

        # None 값 처리 (파싱 실패한 경우)
        if calories is None or cost is None:
            # 파싱되지 않은 레시피는 일단 포함 (LLM으로 재파싱)
            return True

        # 칼로리 체크
        calorie_ok = abs(calories - target_calories) <= calorie_tolerance

        # 비용 체크
        cost_ok = abs(cost - target_cost) <= cost_tolerance

        return calorie_ok and cost_ok

    def calculate_similarity_score(
        self,
        recipe: Dict,
        target_calories: int,
        target_cost: int
    ) -> float:
        """
        유사도 점수 계산 (낮을수록 유사)

        Args:
            recipe: 레시피 딕셔너리
            target_calories: 목표 칼로리
            target_cost: 목표 비용

        Returns:
            유사도 점수 (차이의 합)
        """
        # None 처리: Tavily 검색 결과에서 파싱 실패 시 target 값 사용
        calories = recipe.get("calories") or target_calories
        cost = recipe.get("cost") or target_cost

        # 칼로리 차이 (절대값)
        cal_diff = abs(calories - target_calories)

        # 비용 차이 (절대값, 가중치 0.01 적용)
        cost_diff = abs(cost - target_cost) * 0.01

        # 총 점수 (낮을수록 좋음)
        score = cal_diff + cost_diff

        return score

    def rank_recipes_by_similarity(
        self,
        recipes: List[Dict],
        target_calories: int,
        target_cost: int
    ) -> List[Dict]:
        """
        레시피를 유사도로 정렬

        Args:
            recipes: 레시피 리스트
            target_calories: 목표 칼로리
            target_cost: 목표 비용

        Returns:
            정렬된 레시피 리스트 (유사한 순)
        """
        # 유사도 점수 계산 및 정렬
        scored = [
            {
                **recipe,
                "similarity_score": self.calculate_similarity_score(
                    recipe, target_calories, target_cost
                )
            }
            for recipe in recipes
        ]

        # 점수로 정렬 (낮은 점수 = 더 유사)
        sorted_recipes = sorted(scored, key=lambda x: x["similarity_score"])

        logger.info(
            "recipes_ranked",
            total=len(sorted_recipes),
            top_score=sorted_recipes[0]["similarity_score"] if sorted_recipes else None
        )

        return sorted_recipes

    async def search_alternative_recipes(
        self,
        current_menu_name: str,
        target_calories: int,
        target_cost: int,
        calorie_tolerance: int = 50,
        cost_tolerance: int = 1000,
        restrictions: Optional[List[str]] = None,
        exclude_recipes: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        대체 레시피 검색 (메인 메서드)

        Args:
            current_menu_name: 현재 메뉴 이름
            target_calories: 목표 칼로리
            target_cost: 목표 비용
            calorie_tolerance: 칼로리 허용 범위 (±kcal)
            cost_tolerance: 비용 허용 범위 (±원)
            restrictions: 제외 재료 리스트
            exclude_recipes: 제외 레시피 이름 리스트

        Returns:
            상위 3개 대체 레시피 리스트
        """
        restrictions = restrictions or []
        exclude_recipes = exclude_recipes or []

        # 1. 검색 쿼리 생성
        query = self.build_search_query(
            base_menu=current_menu_name,
            target_calories=target_calories,
            restrictions=restrictions
        )

        # 2. Tavily로 검색 (최대 15개)
        search_results = await self.search_with_tavily(query, max_results=15)

        # 3. 결과 파싱
        candidates = []
        for result in search_results:
            recipe = self.parse_recipe_from_search_result(result)
            if recipe:
                # 제외 레시피 필터링
                if recipe["name"] not in exclude_recipes:
                    # 허용 범위 체크 (일단 통과시킴, LLM 파싱 후 재필터링)
                    if self.is_within_tolerance(
                        recipe, target_calories, target_cost,
                        calorie_tolerance, cost_tolerance
                    ):
                        candidates.append(recipe)

        logger.info(
            "alternative_search_filtering_complete",
            total_results=len(search_results),
            after_filter=len(candidates)
        )

        # 4. 유사도로 정렬
        ranked = self.rank_recipes_by_similarity(
            candidates, target_calories, target_cost
        )

        # 5. 상위 3개 반환
        top_3 = ranked[:3]

        logger.info(
            "alternative_recipes_found",
            current_menu=current_menu_name,
            alternatives_count=len(top_3)
        )

        return top_3


# 싱글톤 인스턴스 생성 함수
_alternative_search_service: Optional[AlternativeRecipeSearchService] = None


def get_alternative_recipe_service() -> AlternativeRecipeSearchService:
    """AlternativeRecipeSearchService 싱글톤 인스턴스 반환"""
    global _alternative_search_service

    if _alternative_search_service is None:
        # 환경 변수에서 API 키 가져오기
        from app.config import settings
        tavily_api_key = settings.TAVILY_API_KEY
        _alternative_search_service = AlternativeRecipeSearchService(
            tavily_api_key=tavily_api_key
        )

    return _alternative_search_service
