"""EC-005, EC-006: State Management Edge Cases

CRITICAL: Tests for unbounded list growth (memory leak) fixes
"""
import pytest
from app.models.state import (
    limit_validation_results,
    limit_events,
    ValidationResult,
)


class TestStateReducerEdges:
    """EC-005, EC-006: Memory Management with Custom Reducers"""

    def test_ec005_1_validation_results_max_limit(self):
        """EC-005-1: validation_results should be capped at MAX_VALIDATION_HISTORY (10)"""
        # Arrange: Simulate 7-day plan with 3 retries per meal
        existing_results = []

        # Simulate adding validation results over time
        for day in range(1, 8):
            for meal in range(3):
                for retry in range(3):
                    for validator in ["nutrition", "allergy", "time"]:
                        new_result = [
                            ValidationResult(
                                validator=validator,
                                passed=False,
                                issues=[f"Day{day} Meal{meal} Retry{retry}"],
                            )
                        ]
                        existing_results = limit_validation_results(
                            existing_results, new_result
                        )

        # Assert: Should only keep last 10 results
        assert len(existing_results) == 10

        # Assert: Should have kept the most recent ones
        assert "Day7" in existing_results[-1].issues[0]  # Last day
        assert "Day6" in existing_results[0].issues[0] or "Day7" in existing_results[0].issues[0]

    def test_ec005_2_validation_results_under_limit(self):
        """EC-005-2: validation_results under limit should keep all"""
        # Arrange: Only 5 results
        existing = []
        for i in range(5):
            new_result = [
                ValidationResult(
                    validator="nutrition",
                    passed=True,
                    issues=[],
                )
            ]
            existing = limit_validation_results(existing, new_result)

        # Assert: Should keep all 5
        assert len(existing) == 5

    def test_ec005_3_validation_results_empty_to_new(self):
        """EC-005-3: Adding to empty validation_results"""
        # Arrange
        existing = []
        new_results = [
            ValidationResult(validator="nutrition", passed=True, issues=[]),
            ValidationResult(validator="allergy", passed=True, issues=[]),
        ]

        # Act
        result = limit_validation_results(existing, new_results)

        # Assert
        assert len(result) == 2
        assert result[0].validator == "nutrition"
        assert result[1].validator == "allergy"

    def test_ec006_1_events_max_limit(self):
        """EC-006-1: events should be capped at MAX_EVENT_HISTORY (20)"""
        # Arrange: Simulate many events
        existing_events = []

        for i in range(50):
            new_event = [
                {
                    "type": "progress",
                    "node": "test_node",
                    "status": "running",
                    "data": {"event_number": i},
                }
            ]
            existing_events = limit_events(existing_events, new_event)

        # Assert: Should only keep last 20
        assert len(existing_events) == 20

        # Assert: Should have kept the most recent ones (30-49)
        assert existing_events[0]["data"]["event_number"] == 30
        assert existing_events[-1]["data"]["event_number"] == 49

    def test_ec006_2_events_under_limit(self):
        """EC-006-2: events under limit should keep all"""
        # Arrange: Only 10 events
        existing = []
        for i in range(10):
            new_event = [{"type": "progress", "data": {"num": i}}]
            existing = limit_events(existing, new_event)

        # Assert: Should keep all 10
        assert len(existing) == 10

    def test_ec006_3_events_batch_addition(self):
        """EC-006-3: Adding multiple events at once"""
        # Arrange
        existing = []
        new_events = [
            {"type": "progress", "data": {"step": 1}},
            {"type": "progress", "data": {"step": 2}},
            {"type": "complete", "data": {"step": 3}},
        ]

        # Act
        result = limit_events(existing, new_events)

        # Assert
        assert len(result) == 3
        assert result[0]["data"]["step"] == 1
        assert result[2]["type"] == "complete"

    def test_ec005_4_validation_results_memory_footprint(self):
        """EC-005-4: Verify memory usage stays bounded"""
        # Arrange: Add way more than limit
        existing = []

        for i in range(100):
            new_result = [
                ValidationResult(
                    validator=f"validator_{i % 3}",
                    passed=i % 2 == 0,
                    issues=[f"Issue {i}"] if i % 2 != 0 else [],
                    reason=f"Reason {i}",
                    details={"iteration": i, "data": "x" * 100},  # Some data
                )
            ]
            existing = limit_validation_results(existing, new_result)

        # Assert: Memory stays bounded
        assert len(existing) == 10

        # Rough memory check (each result should be small)
        import sys
        total_size = sys.getsizeof(existing)
        # Should be much less than if we kept all 100 results
        # This is just a sanity check, not exact measurement
        assert total_size < 10000  # Less than 10KB for the list itself
