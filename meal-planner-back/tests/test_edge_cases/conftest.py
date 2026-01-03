"""Shared fixtures for edge case testing"""
import pytest
from app.models.state import (
    MealPlanState,
    UserProfile,
    MacroTargets,
    Menu,
    MealRecommendation,
    ValidationResult,
)


@pytest.fixture
def minimal_profile():
    """Minimal valid profile for testing"""
    return UserProfile(
        goal="유지",
        weight=70.0,
        height=170.0,
        age=30,
        gender="male",
        activity_level="moderate",
        restrictions=[],
        health_conditions=[],
        budget=50000,
        budget_type="weekly",
        cooking_time="30분 이내",
        skill_level="중급",
        meals_per_day=3,
        days=1,
    )


@pytest.fixture
def macro_targets():
    """Standard macro targets"""
    return MacroTargets(
        calories=2000.0,
        carb_g=250.0,
        protein_g=150.0,
        fat_g=67.0,
        carb_ratio=50,
        protein_ratio=30,
        fat_ratio=20,
    )


@pytest.fixture
def empty_state(minimal_profile, macro_targets):
    """State with no recommendations"""
    return {
        "profile": minimal_profile,
        "daily_targets": macro_targets,
        "per_meal_targets": MacroTargets(
            calories=667.0,
            carb_g=83.0,
            protein_g=50.0,
            fat_g=22.0,
            carb_ratio=50,
            protein_ratio=30,
            fat_ratio=20,
        ),
        "per_meal_budget": 16666,
        "current_day": 1,
        "current_meal_type": "아침",
        "current_meal_index": 0,
        "retry_count": 0,
        "max_retries": 5,
        "nutritionist_recommendation": None,
        "chef_recommendation": None,
        "budget_recommendation": None,
        "current_menu": None,
        "validation_results": [],
        "events": [],
        "completed_meals": [],
        "weekly_plan": [],
        "error_message": None,
        "previous_validation_failures": [],
    }


@pytest.fixture
def mock_menu():
    """Standard mock menu"""
    return Menu(
        meal_type="아침",
        menu_name="테스트 메뉴",
        ingredients=[
            {"name": "닭가슴살", "amount": "150g", "amount_g": 150.0},
            {"name": "현미밥", "amount": "210g", "amount_g": 210.0},
        ],
        calories=550.0,
        carb_g=70.0,
        protein_g=40.0,
        fat_g=10.0,
        sodium_mg=400.0,
        sugar_g=5.0,
        cooking_time_minutes=15,
        estimated_cost=4000,
        recipe_steps=["재료 준비", "조리", "완성"],
    )


@pytest.fixture
def mock_recommendation():
    """Standard mock recommendation"""
    return MealRecommendation(
        menu_name="추천 메뉴",
        ingredients=[
            {"name": "닭가슴살", "amount": "150g", "amount_g": 150.0},
            {"name": "현미밥", "amount": "210g", "amount_g": 210.0},
        ],
        estimated_calories=550.0,
        estimated_cost=4000,
        cooking_time_minutes=15,
        reasoning="영양 균형이 좋음",
    )


@pytest.fixture
def validation_result_pass():
    """Validation result that passed"""
    return ValidationResult(
        validator="nutrition_checker",
        passed=True,
        issues=[],
        reason="영양 목표 충족",
    )


@pytest.fixture
def validation_result_fail():
    """Validation result that failed"""
    return ValidationResult(
        validator="nutrition_checker",
        passed=False,
        issues=["칼로리 초과: 800kcal (목표: 667kcal)"],
        reason="칼로리 20% 초과",
    )


@pytest.fixture
def standard_profile():
    """표준 프로필 (다이어트, 3끼, 7일)"""
    return UserProfile(
        goal="다이어트",
        weight=70.0,
        height=175.0,
        age=30,
        gender="male",
        activity_level="moderate",
        restrictions=[],
        health_conditions=[],
        budget=100_000,
        budget_type="weekly",
        cooking_time="30분 이내",
        skill_level="중급",
        meals_per_day=3,
        days=7,
    )


@pytest.fixture
def constrained_profile():
    """제약 많은 프로필 (저예산, 건강제약, 4끼, 7일)"""
    return UserProfile(
        goal="질병관리",
        weight=75.0,
        height=170.0,
        age=50,
        gender="male",
        activity_level="low",
        restrictions=[],
        health_conditions=["당뇨", "고혈압"],
        budget=70_000,  # per_meal = 70000 / (4 * 7) = 2500원
        budget_type="weekly",
        cooking_time="30분 이내",
        skill_level="초급",
        meals_per_day=4,
        days=7,
    )


@pytest.fixture
def mock_menu_factory():
    """Menu 객체 생성 factory (deterministic values)"""
    def create_menu(
        meal_type="아침",
        calories=500.0,
        cost=4000,
        carb_g=62.5,  # 50% of calories
        protein_g=37.5,  # 30% of calories
        fat_g=11.1,  # 20% of calories
        sodium_mg=800.0,
        sugar_g=15.0,
    ):
        return Menu(
            meal_type=meal_type,
            menu_name=f"{meal_type} 테스트 메뉴",
            ingredients=[
                {"name": "재료1", "amount": "100g", "amount_g": 100.0},
                {"name": "재료2", "amount": "50g", "amount_g": 50.0},
            ],
            calories=calories,
            carb_g=carb_g,
            protein_g=protein_g,
            fat_g=fat_g,
            sodium_mg=sodium_mg,
            sugar_g=sugar_g,
            cooking_time_minutes=20,
            estimated_cost=cost,
            recipe_steps=["조리법 1", "조리법 2"],
            validation_warnings=[],
        )
    return create_menu
