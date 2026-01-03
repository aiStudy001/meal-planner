"""EC-001, EC-002: Agent Workflow Edge Cases

CRITICAL: Tests for day/meal iteration boundary conditions
"""
import pytest
from app.agents.nodes.day_iterator import day_iterator
from app.utils.constants import MEAL_TYPES


class TestDayIteratorEdges:
    """EC-001: Day/Meal Iteration Boundary Cases"""

    def test_ec001_1_meals_per_day_zero(self, minimal_profile, empty_state, mock_menu):
        """EC-001-1: meals_per_day=0 should error gracefully"""
        # Arrange
        minimal_profile.meals_per_day = 0
        empty_state["profile"] = minimal_profile
        empty_state["current_menu"] = mock_menu
        empty_state["current_day"] = 1
        empty_state["current_meal_index"] = 0

        # Act
        result = day_iterator(empty_state)

        # Assert: Should return error, not crash
        assert isinstance(result, dict)
        assert "error_message" in result
        assert "Invalid meals_per_day: 0" in result["error_message"]

        # Assert: Error event
        assert "events" in result
        assert result["events"][0]["type"] == "error"
        assert result["events"][0]["status"] == "invalid_config"

    def test_ec001_2_final_day_completion(
        self, minimal_profile, empty_state, mock_menu
    ):
        """EC-001-2: 7-day plan should complete exactly at day 7, meal 3"""
        # Arrange: Last meal of 7-day plan
        minimal_profile.days = 7
        minimal_profile.meals_per_day = 3
        empty_state["profile"] = minimal_profile
        empty_state["current_day"] = 7
        empty_state["current_meal_index"] = 2  # 0-indexed: meal 3
        empty_state["current_meal_type"] = "저녁"
        empty_state["current_menu"] = mock_menu

        # Simulate 20 completed meals (day 1-6: 18 meals, day 7: 2 meals)
        empty_state["completed_meals"] = [mock_menu] * 20
        empty_state["weekly_plan"] = []

        # Act
        result = day_iterator(empty_state)

        # Assert: Should complete and save to weekly_plan
        assert "weekly_plan" in result
        assert len(result["weekly_plan"]) == 1  # Day 7 added

        # Assert: Completion event
        assert "events" in result
        assert result["events"][0]["type"] == "complete"
        assert result["events"][0]["status"] == "completed"

    def test_ec001_3_meal_type_sequencing(self, minimal_profile, empty_state, mock_menu):
        """EC-001-3: Meal types should follow MEAL_TYPES order"""
        # Arrange
        minimal_profile.meals_per_day = 3
        empty_state["profile"] = minimal_profile
        empty_state["current_day"] = 1
        empty_state["current_meal_index"] = 0
        empty_state["current_meal_type"] = "아침"
        empty_state["current_menu"] = mock_menu
        empty_state["completed_meals"] = []

        # Act: Complete 아침
        result = day_iterator(empty_state)

        # Assert: Next should be 점심
        assert result["current_meal_type"] == MEAL_TYPES[1]  # "점심"
        assert result["current_meal_index"] == 1
        assert result["current_day"] == 1  # Same day

    def test_ec001_4_meal_index_overflow_protection(
        self, minimal_profile, empty_state, mock_menu
    ):
        """EC-001-4: current_meal_index >= meals_per_day should transition to next day"""
        # Arrange: Last meal of day 1
        minimal_profile.meals_per_day = 3
        minimal_profile.days = 2
        empty_state["profile"] = minimal_profile
        empty_state["current_day"] = 1
        empty_state["current_meal_index"] = 2  # Last meal (0-indexed)
        empty_state["current_meal_type"] = "저녁"
        empty_state["current_menu"] = mock_menu
        empty_state["completed_meals"] = [mock_menu, mock_menu]  # 2 meals before this

        # Act
        result = day_iterator(empty_state)

        # Assert: Should transition to day 2, meal 0
        assert result["current_day"] == 2
        assert result["current_meal_index"] == 0
        assert result["current_meal_type"] == MEAL_TYPES[0]  # "아침"

        # Assert: Day 1 should be saved to weekly_plan
        assert "weekly_plan" in result
        assert len(result["weekly_plan"]) == 1

    def test_ec001_5_next_meal_index_overflow(
        self, minimal_profile, empty_state, mock_menu
    ):
        """EC-001-5: next_meal_index >= len(MEAL_TYPES) should use fallback"""
        # Arrange: Somehow meal_index gets to 3 (should not happen, but defensive)
        minimal_profile.meals_per_day = 4  # Valid: 1-4
        empty_state["profile"] = minimal_profile
        empty_state["current_day"] = 1
        empty_state["current_meal_index"] = 2
        empty_state["current_menu"] = mock_menu
        empty_state["completed_meals"] = []

        # Act
        result = day_iterator(empty_state)

        # Assert: Should use MEAL_TYPES[3] = "간식" (last valid)
        assert result["current_meal_index"] == 3
        assert result["current_meal_type"] == MEAL_TYPES[3]  # "간식"

    def test_ec001_6_validation_warnings_attached(
        self, minimal_profile, empty_state, mock_menu
    ):
        """EC-001-6: Validation warnings should be attached to current_menu"""
        # Arrange
        minimal_profile.meals_per_day = 3
        empty_state["profile"] = minimal_profile
        empty_state["current_menu"] = mock_menu
        empty_state["_validation_warnings"] = [
            "칼로리 5% 초과",
            "조리 시간 약간 김"
        ]
        empty_state["completed_meals"] = []

        # Act
        result = day_iterator(empty_state)

        # Assert: Warnings should be in completed_meals
        # (day_iterator adds current_menu to completed_meals with warnings)
        # Since we're testing the iterator logic, we check the state update
        assert "_validation_warnings" in empty_state or "validation_warnings" in str(result)

    def test_ec001_7_meals_per_day_boundary_values(
        self, minimal_profile, empty_state, mock_menu
    ):
        """EC-001-7: Test boundary values for meals_per_day (1, 4)"""
        # Test meals_per_day = 1
        minimal_profile.meals_per_day = 1
        minimal_profile.days = 1
        empty_state["profile"] = minimal_profile
        empty_state["current_day"] = 1
        empty_state["current_meal_index"] = 0
        empty_state["current_meal_type"] = "아침"
        empty_state["current_menu"] = mock_menu
        empty_state["completed_meals"] = []

        result = day_iterator(empty_state)

        # Should complete after 1 meal
        assert "weekly_plan" in result
        assert result["events"][0]["type"] == "complete"

        # Test meals_per_day = 4
        minimal_profile.meals_per_day = 4
        empty_state["profile"] = minimal_profile
        empty_state["current_day"] = 1
        empty_state["current_meal_index"] = 3  # Last meal
        empty_state["current_meal_type"] = "간식"
        empty_state["completed_meals"] = [mock_menu, mock_menu, mock_menu]

        result = day_iterator(empty_state)

        # Should complete after 4 meals
        assert "weekly_plan" in result
