"""
EC-025: Budget Bounds Validation Tests

Tests for input validation edge cases
"""

import pytest
from pydantic import ValidationError
from app.models.requests import MealPlanRequest


class TestEC025BudgetBoundsValidation:
    """EC-025: Budget bounds validation tests"""

    def test_ec025_1_budget_too_low_absolute_minimum(self):
        """EC-025-1: 예산이 절대 최소값(10,000원) 미만일 때 ValidationError 발생"""
        with pytest.raises(ValidationError) as exc_info:
            MealPlanRequest(
                goal="다이어트",
                weight=70,
                height=175,
                age=30,
                gender="male",
                activity_level="moderate",
                budget=9_999,  # 10,000원 미만
                budget_type="weekly",
                cooking_time="30분 이내",
                skill_level="중급",
                meals_per_day=3,
                days=7,
            )

        errors = exc_info.value.errors()
        assert any("budget" in str(error["loc"]) for error in errors)
        assert any("greater_than_equal" in error["type"] for error in errors)

    def test_ec025_2_budget_too_high_absolute_maximum(self):
        """EC-025-2: 예산이 절대 최대값(1,000,000원) 초과일 때 ValidationError 발생"""
        with pytest.raises(ValidationError) as exc_info:
            MealPlanRequest(
                goal="벌크업",
                weight=80,
                height=180,
                age=25,
                gender="male",
                activity_level="high",
                budget=1_000_001,  # 1,000,000원 초과
                budget_type="weekly",
                cooking_time="제한 없음",
                skill_level="고급",
                meals_per_day=4,
                days=7,
            )

        errors = exc_info.value.errors()
        assert any("budget" in str(error["loc"]) for error in errors)
        assert any("less_than_equal" in error["type"] for error in errors)

    def test_ec025_3_per_meal_budget_too_low(self):
        """EC-025-3: 끼니당 예산이 최소값(2,000원) 미만일 때 ValidationError 발생"""
        with pytest.raises(ValidationError) as exc_info:
            MealPlanRequest(
                goal="다이어트",
                weight=65,
                height=170,
                age=28,
                gender="female",
                activity_level="low",
                budget=40_000,  # 40,000원 / (3끼 * 7일) = 1,904원/끼니 < 2,000원
                budget_type="weekly",
                cooking_time="15분 이내",
                skill_level="초급",
                meals_per_day=3,
                days=7,
            )

        # Model validator error doesn't have "loc" in the same way
        error_msg = str(exc_info.value)
        assert "끼니당 예산이 너무 낮습니다" in error_msg
        assert "2,000원/끼니" in error_msg

    def test_ec025_4_valid_budget_within_bounds(self):
        """EC-025-4: 유효한 예산 범위 내에서 요청이 정상 통과"""
        # 끼니당 3,000원 (63,000원 / 21끼니)
        request = MealPlanRequest(
            goal="유지",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            budget=63_000,  # 적정 예산
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        # 검증 통과 확인
        assert request.budget == 63_000
        assert request.meals_per_day == 3
        assert request.days == 7

        # 끼니당 예산 계산
        per_meal_budget = request.budget / (request.meals_per_day * request.days)
        assert per_meal_budget >= 2_000  # 최소 기준 충족

    def test_ec025_5_edge_case_budgets_at_boundaries(self):
        """EC-025-5: 경계값 테스트 (정확히 최소/최대값)"""
        # 최소 예산 (10,000원) - 통과해야 함
        request_min = MealPlanRequest(
            goal="다이어트",
            weight=60,
            height=165,
            age=25,
            gender="female",
            activity_level="low",
            budget=10_000,  # 정확히 최소값
            budget_type="daily",  # 하루 10,000원 = 끼니당 3,333원
            cooking_time="15분 이내",
            skill_level="초급",
            meals_per_day=3,
            days=1,
        )
        assert request_min.budget == 10_000

        # 최대 예산 (1,000,000원) - 통과해야 함
        request_max = MealPlanRequest(
            goal="벌크업",
            weight=90,
            height=185,
            age=30,
            gender="male",
            activity_level="very_high",
            budget=1_000_000,  # 정확히 최대값
            budget_type="weekly",
            cooking_time="제한 없음",
            skill_level="고급",
            meals_per_day=4,
            days=7,
        )
        assert request_max.budget == 1_000_000

        # 끼니당 정확히 2,000원 (최소 기준) - 통과해야 함
        request_exact_min = MealPlanRequest(
            goal="유지",
            weight=70,
            height=175,
            age=30,
            gender="male",
            activity_level="moderate",
            budget=42_000,  # 42,000원 / 21끼니 = 2,000원/끼니
            budget_type="weekly",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )
        assert request_exact_min.budget == 42_000
        per_meal = request_exact_min.budget / (request_exact_min.meals_per_day * request_exact_min.days)
        assert per_meal == 2_000.0
