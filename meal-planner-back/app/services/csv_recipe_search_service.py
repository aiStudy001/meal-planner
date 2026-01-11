"""
CSV 기반 레시피 검색 서비스

로컬 레시피 CSV 파일에서 유사한 레시피 검색
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from app.utils.logging import get_logger

logger = get_logger(__name__)

# CSV 파일 경로
CSV_PATH = Path(__file__).parent.parent.parent / "data" / "recipes_with_nutrition.csv"


class CSVRecipeSearchService:
    """CSV 기반 레시피 검색 서비스"""

    def __init__(self):
        """서비스 초기화 및 CSV 로드"""
        self.recipes_df = None
        self._load_csv()

    def _load_csv(self):
        """CSV 파일 로드"""
        try:
            if not CSV_PATH.exists():
                logger.error(
                    "csv_file_not_found",
                    path=str(CSV_PATH)
                )
                raise FileNotFoundError(f"Recipe CSV not found: {CSV_PATH}")

            # CSV 로드 (encoding 자동 감지)
            self.recipes_df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')

            # 필수 컬럼 확인
            required_cols = ['name', 'calories', 'difficulty', 'cooking_time', 'ingredients_parsed']
            missing_cols = [col for col in required_cols if col not in self.recipes_df.columns]

            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # 결측값 처리
            self.recipes_df['calories'] = pd.to_numeric(self.recipes_df['calories'], errors='coerce').fillna(0)
            self.recipes_df['cooking_time'] = pd.to_numeric(self.recipes_df['cooking_time'], errors='coerce').fillna(30)
            self.recipes_df['difficulty'] = self.recipes_df['difficulty'].fillna('중급')

            logger.info(
                "csv_loaded_successfully",
                total_recipes=len(self.recipes_df),
                path=str(CSV_PATH)
            )

        except Exception as e:
            logger.error("csv_load_failed", error=str(e))
            raise

    def _parse_ingredients(self, ingredients_str: str) -> List[str]:
        """
        재료 문자열을 파싱하여 재료명 리스트 반환

        Args:
            ingredients_str: JSON 형식의 재료 문자열

        Returns:
            재료명 리스트
        """
        try:
            if pd.isna(ingredients_str) or not ingredients_str:
                return []

            ingredients_data = json.loads(ingredients_str)
            return [ing.get('name', '') for ing in ingredients_data if ing.get('name')]
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("ingredient_parse_failed", error=str(e))
            return []

    def _has_restricted_ingredients(
        self,
        recipe_ingredients: List[str],
        restrictions: List[str]
    ) -> bool:
        """
        레시피에 제한 재료가 포함되어 있는지 확인

        Args:
            recipe_ingredients: 레시피 재료 리스트
            restrictions: 제외 재료 리스트

        Returns:
            제한 재료 포함 여부
        """
        if not restrictions:
            return False

        # 재료명 정규화 (소문자, 공백 제거)
        normalized_ingredients = [ing.lower().replace(' ', '') for ing in recipe_ingredients]
        normalized_restrictions = [r.lower().replace(' ', '') for r in restrictions]

        # 부분 매칭 (예: "계란" in "계란말이")
        for restriction in normalized_restrictions:
            for ingredient in normalized_ingredients:
                if restriction in ingredient or ingredient in restriction:
                    return True

        return False

    def _calculate_macro_ratio_score(
        self,
        recipe_carb_g: float,
        recipe_protein_g: float,
        recipe_fat_g: float,
        target_carb_g: float,
        target_protein_g: float,
        target_fat_g: float
    ) -> float:
        """
        탄단지 비율 유사도 점수 계산 (0-100, 낮을수록 유사)

        Args:
            recipe_carb_g: 레시피 탄수화물(g)
            recipe_protein_g: 레시피 단백질(g)
            recipe_fat_g: 레시피 지방(g)
            target_carb_g: 목표 탄수화물(g)
            target_protein_g: 목표 단백질(g)
            target_fat_g: 목표 지방(g)

        Returns:
            탄단지 비율 차이 점수 (낮을수록 유사, 0-100 범위)
        """
        # 레시피 비율 계산 (%)
        recipe_total = recipe_carb_g + recipe_protein_g + recipe_fat_g
        if recipe_total == 0:
            return 100.0  # 영양정보 없음 = 최악의 점수

        recipe_ratios = {
            'carb': (recipe_carb_g / recipe_total) * 100,
            'protein': (recipe_protein_g / recipe_total) * 100,
            'fat': (recipe_fat_g / recipe_total) * 100,
        }

        # 목표 비율 계산 (%)
        target_total = target_carb_g + target_protein_g + target_fat_g
        if target_total == 0:
            return 0.0  # 목표가 없으면 비율 고려 안함

        target_ratios = {
            'carb': (target_carb_g / target_total) * 100,
            'protein': (target_protein_g / target_total) * 100,
            'fat': (target_fat_g / target_total) * 100,
        }

        # 각 영양소 비율 차이의 합 (퍼센트 포인트)
        total_diff = sum(
            abs(recipe_ratios[k] - target_ratios[k])
            for k in ['carb', 'protein', 'fat']
        )

        # 0-100 범위로 제한 (최대 차이 = 각 영양소 100%씩 차이 = 300%, 하지만 실제로는 100 이하)
        return min(total_diff, 100.0)

    def _calculate_similarity_score(
        self,
        recipe_calories: float,
        target_calories: int,
        recipe_difficulty: str,
        target_difficulty: str,
        recipe_time: int,
        target_time: int,
        recipe_carb_g: Optional[float] = None,
        recipe_protein_g: Optional[float] = None,
        recipe_fat_g: Optional[float] = None,
        target_carb_g: Optional[float] = None,
        target_protein_g: Optional[float] = None,
        target_fat_g: Optional[float] = None
    ) -> float:
        """
        유사도 점수 계산 (낮을수록 유사)

        Args:
            recipe_calories: 레시피 칼로리
            target_calories: 목표 칼로리
            recipe_difficulty: 레시피 난이도
            target_difficulty: 목표 난이도 (선택사항)
            recipe_time: 조리 시간
            target_time: 목표 조리 시간 (선택사항)
            recipe_carb_g: 레시피 탄수화물(g) - 선택사항
            recipe_protein_g: 레시피 단백질(g) - 선택사항
            recipe_fat_g: 레시피 지방(g) - 선택사항
            target_carb_g: 목표 탄수화물(g) - 선택사항
            target_protein_g: 목표 단백질(g) - 선택사항
            target_fat_g: 목표 지방(g) - 선택사항

        Returns:
            유사도 점수 (낮을수록 좋음)
        """
        # 칼로리 차이 점수 (정규화: 0-100 스케일)
        calorie_diff = abs(recipe_calories - target_calories)
        calorie_score = min(calorie_diff / 10, 100)  # 1000kcal 차이 = 100점

        # 조리 시간 차이 점수 (정규화: 0-100 스케일)
        time_score = 0
        if target_time:
            time_diff = abs(recipe_time - target_time)
            time_score = min(time_diff / 2, 100)  # 200분 차이 = 100점

        # 난이도 페널티 (0-50 스케일)
        difficulty_penalty = 0
        difficulty_map = {'초급': 0, '중급': 10, '고급': 20}
        if target_difficulty:
            target_level = difficulty_map.get(target_difficulty, 10)
            recipe_level = difficulty_map.get(recipe_difficulty, 10)
            if recipe_level > target_level:
                difficulty_penalty = 50  # 더 어려운 난이도에 페널티

        # 탄단지 비율 점수 (0-100 스케일)
        macro_score = 0
        use_macro_scoring = all([
            recipe_carb_g is not None,
            recipe_protein_g is not None,
            recipe_fat_g is not None,
            target_carb_g is not None,
            target_protein_g is not None,
            target_fat_g is not None
        ])

        if use_macro_scoring:
            macro_score = self._calculate_macro_ratio_score(
                recipe_carb_g, recipe_protein_g, recipe_fat_g,
                target_carb_g, target_protein_g, target_fat_g
            )
            # 가중치 적용: 칼로리 40%, 탄단지 50%, 시간 10%
            score = (calorie_score * 0.4) + (macro_score * 0.5) + (time_score * 0.1) + difficulty_penalty
        else:
            # 탄단지 정보 없을 때: 기존 로직 (칼로리 위주)
            score = calorie_score + (time_score * 0.5) + difficulty_penalty

        return score

    async def search_alternative_recipes(
        self,
        current_menu_name: str,
        target_calories: int,
        target_cost: int = 0,  # CSV에 비용 정보 없으므로 사용 안함
        calorie_tolerance: int = 100,
        cost_tolerance: int = 2000,  # 사용 안함
        restrictions: Optional[List[str]] = None,
        exclude_recipes: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        max_cooking_time: Optional[int] = None,
        target_carb_g: Optional[float] = None,
        target_protein_g: Optional[float] = None,
        target_fat_g: Optional[float] = None
    ) -> List[Dict]:
        """
        CSV에서 대체 레시피 검색

        Args:
            current_menu_name: 현재 메뉴 이름
            target_calories: 목표 칼로리
            target_cost: 목표 비용 (사용 안함)
            calorie_tolerance: 칼로리 허용 범위
            cost_tolerance: 비용 허용 범위 (사용 안함)
            restrictions: 제외 재료 리스트
            exclude_recipes: 제외 레시피 이름 리스트
            difficulty: 난이도 제한 (초급/중급/고급)
            max_cooking_time: 최대 조리 시간
            target_carb_g: 목표 탄수화물(g) - 선택사항
            target_protein_g: 목표 단백질(g) - 선택사항
            target_fat_g: 목표 지방(g) - 선택사항

        Returns:
            상위 3개 대체 레시피 리스트
        """
        restrictions = restrictions or []
        exclude_recipes = exclude_recipes or []

        logger.info(
            "csv_search_started",
            current_menu=current_menu_name,
            target_calories=target_calories,
            restrictions=restrictions,
            calorie_tolerance=calorie_tolerance
        )

        # 데이터프레임 복사
        df = self.recipes_df.copy()
        logger.info("csv_initial_count", count=len(df))

        # 1. 현재 레시피 제외
        if current_menu_name:
            df = df[df['name'] != current_menu_name]
            logger.info("csv_after_exclude_current", count=len(df), excluded=current_menu_name)

        # 2. 제외 레시피 필터링
        if exclude_recipes:
            df = df[~df['name'].isin(exclude_recipes)]
            logger.info("csv_after_exclude_list", count=len(df), excluded_count=len(exclude_recipes))

        # 3. 칼로리 범위 필터링
        min_cal = target_calories - calorie_tolerance
        max_cal = target_calories + calorie_tolerance
        df = df[(df['calories'] >= min_cal) & (df['calories'] <= max_cal)]
        logger.info(
            "csv_after_calorie_filter",
            count=len(df),
            min_cal=min_cal,
            max_cal=max_cal
        )

        # 4. 조리 시간 필터링
        if max_cooking_time:
            df = df[df['cooking_time'] <= max_cooking_time]
            logger.info("csv_after_time_filter", count=len(df), max_time=max_cooking_time)

        # 5. 재료 제한 필터링
        if restrictions:
            def filter_by_restrictions(row):
                ingredients = self._parse_ingredients(row['ingredients_parsed'])
                return not self._has_restricted_ingredients(ingredients, restrictions)

            df = df[df.apply(filter_by_restrictions, axis=1)]
            logger.info("csv_after_restrictions_filter", count=len(df))

        logger.info(
            "csv_search_after_filtering",
            total_candidates=len(df)
        )

        if len(df) == 0:
            logger.warning("no_recipes_found_after_filtering")
            return []

        # 6. 유사도 점수 계산
        df['similarity_score'] = df.apply(
            lambda row: self._calculate_similarity_score(
                recipe_calories=row['calories'],
                target_calories=target_calories,
                recipe_difficulty=row['difficulty'],
                target_difficulty=difficulty,
                recipe_time=row['cooking_time'],
                target_time=max_cooking_time or 30,
                recipe_carb_g=row.get('carb_g'),
                recipe_protein_g=row.get('protein_g'),
                recipe_fat_g=row.get('fat_g'),
                target_carb_g=target_carb_g,
                target_protein_g=target_protein_g,
                target_fat_g=target_fat_g
            ),
            axis=1
        )

        # 7. 점수로 정렬 (낮은 점수 = 더 유사)
        df = df.sort_values('similarity_score')

        # 8. 상위 3개 선택
        top_recipes = df.head(3)

        # 9. 결과 포맷팅
        results = []
        for _, row in top_recipes.iterrows():
            ingredients = self._parse_ingredients(row['ingredients_parsed'])

            recipe = {
                "name": row['name'],
                "url": "",  # CSV에는 URL 정보 없음
                "content_preview": f"{row.get('category', '')} - {row.get('main_ingredient', '')}",
                "calories": int(row['calories']) if pd.notna(row['calories']) else None,
                "cost": None,  # CSV에 비용 정보 없음
                "cooking_time": int(row['cooking_time']) if pd.notna(row['cooking_time']) else None,
                "difficulty": row['difficulty'],
                "ingredients": ingredients[:5]  # 처음 5개 재료만
            }
            results.append(recipe)

        logger.info(
            "csv_search_completed",
            current_menu=current_menu_name,
            alternatives_count=len(results)
        )

        return results


# 싱글톤 인스턴스
_csv_search_service: Optional[CSVRecipeSearchService] = None


def get_csv_recipe_service() -> CSVRecipeSearchService:
    """CSVRecipeSearchService 싱글톤 인스턴스 반환"""
    global _csv_search_service

    if _csv_search_service is None:
        _csv_search_service = CSVRecipeSearchService()

    return _csv_search_service
