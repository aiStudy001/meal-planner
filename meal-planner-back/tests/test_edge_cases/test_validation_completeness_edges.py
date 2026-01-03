"""EC-023, EC-024: Validation Completeness Edge Cases

CRITICAL: Tests for health constraints and budget validation
"""
import pytest
from app.models.state import MealPlanState, UserProfile, Menu, ValidationResult


class TestHealthConstraintsValidation:
    """EC-023: Health Constraints Validator"""

    @pytest.mark.asyncio
    async def test_ec023_1_diabetes_sugar_constraint_pass(self):
        """EC-023-1: Diabetes sugar constraint passes when within limit"""
        # Arrange
        from app.agents.nodes.validation.health_checker import health_checker

        profile = UserProfile(
            goal="질병관리",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=["당뇨"],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="저당 오트밀",
            calories=350,
            carb_g=50,  # 30% = 15g sugar (< 30g limit)
            protein_g=20,
            fat_g=10,
            sodium_mg=200,
            sugar_g=15.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "오트밀", "amount": "100g"},
                {"name": "우유", "amount": "200ml"},
                {"name": "블루베리", "amount": "50g"}
            ],
            recipe_steps=["오트밀 끓이기"],
            recipe_url="http://example.com",
            cooking_time_minutes=10,
            estimated_cost=5000,
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 0,
            "current_day": 1,
            "current_meal_index": 0,
            "current_meal_type": "아침",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 0,
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await health_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "health_checker"
        assert validation.passed is True, "Should pass when sugar ≤ 30g"
        assert len(validation.issues) == 0

    @pytest.mark.asyncio
    async def test_ec023_2_diabetes_sugar_constraint_fail(self):
        """EC-023-2: Diabetes sugar constraint fails when exceeding limit"""
        # Arrange
        from app.agents.nodes.validation.health_checker import health_checker

        profile = UserProfile(
            goal="질병관리",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=["당뇨"],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="달콤한 팬케이크",
            calories=600,
            carb_g=120,  # 30% = 36g sugar (> 30g limit)
            protein_g=15,
            fat_g=20,
            sodium_mg=300,
            sugar_g=36.0,  # Estimated 30% of carbs (exceeds limit)
            ingredients=[
                {"name": "밀가루", "amount": "150g"},
                {"name": "설탕", "amount": "30g"},
                {"name": "시럽", "amount": "50ml"}
            ],
            recipe_steps=["팬케이크 만들기"],
            recipe_url="http://example.com",
            cooking_time_minutes=15,
            estimated_cost=7000,
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 0,
            "current_day": 1,
            "current_meal_index": 0,
            "current_meal_type": "아침",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 0,
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await health_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "health_checker"
        assert validation.passed is False, "Should fail when sugar > 30g"
        assert len(validation.issues) == 1
        assert "당뇨 제약" in validation.issues[0]
        assert "36.0g" in validation.issues[0]  # Estimated sugar

    @pytest.mark.asyncio
    async def test_ec023_3_hypertension_sodium_constraint_fail(self):
        """EC-023-3: Hypertension sodium constraint fails when exceeding limit"""
        # Arrange
        from app.agents.nodes.validation.health_checker import health_checker

        profile = UserProfile(
            goal="질병관리",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=["고혈압"],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="점심",
            menu_name="짠 라면",
            calories=500,
            carb_g=80,
            protein_g=15,
            fat_g=15,
            sodium_mg=2500,  # > 2000mg limit
            sugar_g=24.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "라면", "amount": "1봉"},
                {"name": "소금", "amount": "5g"}
            ],
            recipe_steps=["라면 끓이기"],
            recipe_url="http://example.com",
            cooking_time_minutes=5,
            estimated_cost=3000,
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 0,
            "current_day": 1,
            "current_meal_index": 1,
            "current_meal_type": "점심",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 0,
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await health_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "health_checker"
        assert validation.passed is False, "Should fail when sodium > 2000mg"
        assert len(validation.issues) == 1
        assert "고혈압 제약" in validation.issues[0]
        assert "2500" in validation.issues[0]  # Accept both "2500mg" and "2500.0mg"

    @pytest.mark.asyncio
    async def test_ec023_4_hyperlipidemia_saturated_fat_constraint_fail(self):
        """EC-023-4: Hyperlipidemia saturated fat constraint fails when exceeding limit"""
        # Arrange
        from app.agents.nodes.validation.health_checker import health_checker

        profile = UserProfile(
            goal="질병관리",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=["고지혈증"],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="저녁",
            menu_name="고지방 스테이크",
            calories=800,
            carb_g=30,
            protein_g=50,
            fat_g=50,  # 30% = 15g saturated fat (> 7g limit)
            sodium_mg=1000,
            sugar_g=9.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "소고기", "amount": "200g"},
                {"name": "버터", "amount": "30g"}
            ],
            recipe_steps=["스테이크 굽기"],
            recipe_url="http://example.com",
            cooking_time_minutes=20,
            estimated_cost=25000,
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 0,
            "current_day": 1,
            "current_meal_index": 2,
            "current_meal_type": "저녁",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 0,
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await health_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "health_checker"
        assert validation.passed is False, "Should fail when saturated fat > 7g"
        assert len(validation.issues) == 1
        assert "고지혈증 제약" in validation.issues[0]
        assert "15.0g" in validation.issues[0]  # Estimated saturated fat

    @pytest.mark.asyncio
    async def test_ec023_5_no_health_conditions_auto_pass(self):
        """EC-023-5: No health conditions should auto-pass validation"""
        # Arrange
        from app.agents.nodes.validation.health_checker import health_checker

        profile = UserProfile(
            goal="다이어트",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],  # No health conditions
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="일반 식사",
            calories=500,
            carb_g=100,
            protein_g=30,
            fat_g=20,
            sodium_mg=3000,  # High but should pass because no health conditions
            sugar_g=30.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "밥", "amount": "210g"},
                {"name": "김치", "amount": "50g"}
            ],
            recipe_steps=["밥 짓기"],
            recipe_url="http://example.com",
            cooking_time_minutes=30,
            estimated_cost=5000,
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 0,
            "current_day": 1,
            "current_meal_index": 0,
            "current_meal_type": "아침",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 0,
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await health_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "health_checker"
        assert validation.passed is True, "Should auto-pass when no health conditions"
        assert len(validation.issues) == 0


class TestBudgetValidation:
    """EC-024: Budget Checker Validator"""

    @pytest.mark.asyncio
    async def test_ec024_1_budget_within_110_percent_pass_retry0(self):
        """EC-024-1: Budget within 110% passes on retry 0-2"""
        # Arrange
        from app.agents.nodes.validation.budget_checker import budget_checker

        profile = UserProfile(
            goal="다이어트",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="적당한 식사",
            calories=400,
            carb_g=60,
            protein_g=25,
            fat_g=10,
            sodium_mg=500,
            sugar_g=18.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "밥", "amount": "150g"},
                {"name": "계란", "amount": "1개"},
                {"name": "김치", "amount": "30g"}
            ],
            recipe_steps=["조리"],
            recipe_url="http://example.com",
            cooking_time_minutes=20,
            estimated_cost=5400,  # 109% of 5000 (< 110% tolerance)
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 5000,
            "current_day": 1,
            "current_meal_index": 0,
            "current_meal_type": "아침",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 0,  # First attempt
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await budget_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "budget_checker"
        assert validation.passed is True, "Should pass when cost ≤ 110% of budget"
        assert len(validation.issues) == 0

    @pytest.mark.asyncio
    async def test_ec024_2_budget_exceeds_110_percent_fail_retry0(self):
        """EC-024-2: Budget exceeding 110% fails on retry 0-2"""
        # Arrange
        from app.agents.nodes.validation.budget_checker import budget_checker

        profile = UserProfile(
            goal="다이어트",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="비싼 식사",
            calories=400,
            carb_g=60,
            protein_g=25,
            fat_g=10,
            sodium_mg=500,
            sugar_g=18.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "밥", "amount": "150g"},
                {"name": "계란", "amount": "1개"},
                {"name": "김치", "amount": "30g"}
            ],
            recipe_steps=["조리"],
            recipe_url="http://example.com",
            cooking_time_minutes=20,
            estimated_cost=5600,  # 112% of 5000 (> 110% tolerance)
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 5000,
            "current_day": 1,
            "current_meal_index": 0,
            "current_meal_type": "아침",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 1,  # Retry 1 (still using 10% tolerance)
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await budget_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "budget_checker"
        assert validation.passed is False, "Should fail when cost > 110% of budget"
        assert len(validation.issues) == 1
        assert "예산 초과" in validation.issues[0]
        assert "5,000원" in validation.issues[0]
        assert "5,600원" in validation.issues[0]
        assert "+10% 허용" in validation.issues[0]

    @pytest.mark.asyncio
    async def test_ec024_3_progressive_relaxation_115_percent_retry3(self):
        """EC-024-3: Progressive relaxation allows 115% on retry 3+"""
        # Arrange
        from app.agents.nodes.validation.budget_checker import budget_checker

        profile = UserProfile(
            goal="다이어트",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="조금 비싼 식사",
            calories=400,
            carb_g=60,
            protein_g=25,
            fat_g=10,
            sodium_mg=500,
            sugar_g=18.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "밥", "amount": "150g"},
                {"name": "계란", "amount": "1개"},
                {"name": "김치", "amount": "30g"}
            ],
            recipe_steps=["조리"],
            recipe_url="http://example.com",
            cooking_time_minutes=20,
            estimated_cost=5700,  # 114% of 5000 (< 115% tolerance at retry 3+)
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 5000,
            "current_day": 1,
            "current_meal_index": 0,
            "current_meal_type": "아침",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 3,  # Retry 3+ (progressive relaxation)
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await budget_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "budget_checker"
        assert validation.passed is True, "Should pass when cost ≤ 115% at retry 3+"
        assert len(validation.issues) == 0

    @pytest.mark.asyncio
    async def test_ec024_4_progressive_relaxation_exceeds_115_retry3(self):
        """EC-024-4: Progressive relaxation still fails when exceeding 115% at retry 3+"""
        # Arrange
        from app.agents.nodes.validation.budget_checker import budget_checker

        profile = UserProfile(
            goal="다이어트",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="너무 비싼 식사",
            calories=400,
            carb_g=60,
            protein_g=25,
            fat_g=10,
            sodium_mg=500,
            sugar_g=18.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "밥", "amount": "150g"},
                {"name": "계란", "amount": "1개"},
                {"name": "김치", "amount": "30g"}
            ],
            recipe_steps=["조리"],
            recipe_url="http://example.com",
            cooking_time_minutes=20,
            estimated_cost=5800,  # 116% of 5000 (> 115% tolerance)
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 5000,
            "current_day": 1,
            "current_meal_index": 0,
            "current_meal_type": "아침",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 4,  # Retry 4 (progressive relaxation)
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await budget_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "budget_checker"
        assert validation.passed is False, "Should fail when cost > 115% even at retry 4"
        assert len(validation.issues) == 1
        assert "예산 초과" in validation.issues[0]
        assert "5,000원" in validation.issues[0]
        assert "5,800원" in validation.issues[0]
        assert "+15% 허용" in validation.issues[0]

    @pytest.mark.asyncio
    async def test_ec024_5_exact_budget_match_always_pass(self):
        """EC-024-5: Exact budget match should always pass regardless of retry"""
        # Arrange
        from app.agents.nodes.validation.budget_checker import budget_checker

        profile = UserProfile(
            goal="다이어트",
            weight=70,
            height=170,
            age=30,
            gender="male",
            activity_level="moderate",
            restrictions=[],
            health_conditions=[],
            calorie_adjustment=0,
            macro_ratio={"carb": 50, "protein": 30, "fat": 20},
            budget=300000,
            budget_type="weekly",
            budget_distribution="equal",
            cooking_time="30분 이내",
            skill_level="중급",
            meals_per_day=3,
            days=7,
        )

        menu = Menu(
            meal_type="아침",
            menu_name="정확한 가격 식사",
            calories=400,
            carb_g=60,
            protein_g=25,
            fat_g=10,
            sodium_mg=500,
            sugar_g=18.0,  # Estimated 30% of carbs
            ingredients=[
                {"name": "밥", "amount": "150g"},
                {"name": "계란", "amount": "1개"},
                {"name": "김치", "amount": "30g"}
            ],
            recipe_steps=["조리"],
            recipe_url="http://example.com",
            cooking_time_minutes=20,
            estimated_cost=5000,  # Exact match
            validation_warnings=[],
        )

        state: MealPlanState = {
            "profile": profile,
            "daily_targets": None,
            "per_meal_targets": None,
            "per_meal_budget": 5000,
            "current_day": 1,
            "current_meal_index": 0,
            "current_meal_type": "아침",
            "current_menu": menu,
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "validation_results": [],
            "retry_count": 0,
            "max_retries": 5,
            "error_message": None,
            "completed_meals": [],
            "weekly_plan": [],
            "events": [],
        }

        # Act
        result = await budget_checker(state)

        # Assert
        assert len(result["validation_results"]) == 1
        validation: ValidationResult = result["validation_results"][0]
        assert validation.validator == "budget_checker"
        assert validation.passed is True, "Should pass when cost exactly matches budget"
        assert len(validation.issues) == 0
