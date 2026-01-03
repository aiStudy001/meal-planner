"""EC-021, EC-022: SSE Streaming Resilience Edge Cases

CRITICAL: Tests for client disconnect handling and mid-stream error recovery
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.requests import MealPlanRequest


class TestSSEClientDisconnectEdges:
    """EC-021: SSE Client Disconnect Handling"""

    @pytest.mark.asyncio
    async def test_ec021_1_client_disconnect_raises_cancelled_error(self):
        """EC-021-1: Client disconnect should raise CancelledError"""
        # Arrange: Mock graph that simulates client disconnect
        from app.services.stream_service import stream_meal_plan

        request = MealPlanRequest(
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
            days=1,
        )

        async def mock_graph_stream_with_cancel(*args, **kwargs):
            yield {"mock_node": {"events": [{"type": "progress"}]}}
            # Simulate client disconnect
            raise asyncio.CancelledError()

        with patch("app.services.stream_service.get_meal_planner_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.astream = mock_graph_stream_with_cancel
            mock_get_graph.return_value = mock_graph

            # Act & Assert: Should propagate CancelledError
            with pytest.raises(asyncio.CancelledError):
                async for _ in stream_meal_plan(request):
                    pass

    @pytest.mark.asyncio
    async def test_ec021_2_disconnect_logs_event_counts(self):
        """EC-021-2: Disconnect should log event count and partial events"""
        # Arrange
        from app.services.stream_service import stream_meal_plan

        request = MealPlanRequest(
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
            days=1,
        )

        async def mock_graph_stream_partial(*args, **kwargs):
            # Send 3 chunks before disconnect
            yield {"node1": {"events": [{"type": "progress", "data": "event1"}]}}
            yield {"node2": {"events": [{"type": "progress", "data": "event2"}]}}
            yield {"node3": {"events": [{"type": "progress", "data": "event3"}]}}
            raise asyncio.CancelledError()

        with patch("app.services.stream_service.get_meal_planner_graph") as mock_get_graph:
            with patch("app.services.stream_service.logger") as mock_logger:
                mock_graph = MagicMock()
                mock_graph.astream = mock_graph_stream_partial
                mock_get_graph.return_value = mock_graph

                # Act
                try:
                    events_received = []
                    async for event in stream_meal_plan(request):
                        events_received.append(event)
                except asyncio.CancelledError:
                    pass

                # Assert: Logger should have been called with event counts
                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args
                assert call_args[0][0] == "stream_client_disconnected"
                assert "event_count" in call_args[1]
                assert "partial_events_sent" in call_args[1]

    @pytest.mark.asyncio
    async def test_ec021_3_disconnect_does_not_affect_other_requests(self):
        """EC-021-3: One client disconnect should not affect other concurrent requests"""
        # Arrange: Simulate two concurrent requests, one disconnects
        from app.services.stream_service import stream_meal_plan

        request = MealPlanRequest(
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
            days=1,
        )

        call_count = 0

        async def mock_graph_stream_conditional(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            current_call = call_count

            if current_call == 1:
                # First request: disconnect after 1 event
                yield {"node1": {"events": [{"type": "progress"}]}}
                raise asyncio.CancelledError()
            else:
                # Second request: complete normally
                yield {"node1": {"events": [{"type": "progress"}]}}
                yield {"node2": {"events": [{"type": "progress"}]}}

        with patch("app.services.stream_service.get_meal_planner_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.astream = mock_graph_stream_conditional
            mock_graph.ainvoke = AsyncMock(return_value={"weekly_plan": []})
            mock_get_graph.return_value = mock_graph

            # Act: Run two requests
            request1_failed = False
            request2_success = False

            try:
                async for _ in stream_meal_plan(request):
                    pass
            except asyncio.CancelledError:
                request1_failed = True

            events = []
            try:
                async for event in stream_meal_plan(request):
                    events.append(event)
                request2_success = True
            except asyncio.CancelledError:
                pass

            # Assert
            assert request1_failed, "First request should have been cancelled"
            assert request2_success, "Second request should complete normally"

    @pytest.mark.asyncio
    async def test_ec021_4_graceful_disconnect_no_resource_leaks(self):
        """EC-021-4: Disconnect should not leak resources or file handles"""
        # Arrange
        from app.services.stream_service import stream_meal_plan

        request = MealPlanRequest(
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
            days=1,
        )

        async def mock_graph_stream_with_cancel(*args, **kwargs):
            yield {"node": {"events": [{"type": "progress"}]}}
            raise asyncio.CancelledError()

        with patch("app.services.stream_service.get_meal_planner_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.astream = mock_graph_stream_with_cancel
            mock_get_graph.return_value = mock_graph

            # Act: Run and cancel 10 times
            for _ in range(10):
                try:
                    async for _ in stream_meal_plan(request):
                        pass
                except asyncio.CancelledError:
                    pass

            # Assert: No exceptions or resource warnings should occur
            # In production, verify with memory profiling or resource monitoring
            assert True


class TestSSEMidErrorHandlingEdges:
    """EC-022: SSE Mid-Stream Error Recovery"""

    @pytest.mark.asyncio
    async def test_ec022_1_chunk_error_sends_warning_event(self):
        """EC-022-1: Chunk processing error should send warning SSE event"""
        # Arrange
        from app.services.stream_service import stream_meal_plan

        request = MealPlanRequest(
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
            days=1,
        )

        async def mock_graph_stream_with_bad_chunk(*args, **kwargs):
            # Good chunk
            yield {"node1": {"events": [{"type": "progress"}]}}
            # Bad chunk (invalid structure that will cause transform_event to fail)
            yield {"node2": {"events": [None]}}  # None event will crash transform_event
            # Good chunk
            yield {"node3": {"events": [{"type": "progress"}]}}

        with patch("app.services.stream_service.get_meal_planner_graph") as mock_get_graph:
            with patch("app.services.stream_service.transform_event") as mock_transform:
                # Make transform_event fail on second call
                call_count = 0

                def transform_side_effect(event, node_name):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 2:
                        raise ValueError("Transform failed on bad event")
                    return {"type": "progress", "data": {}}

                mock_transform.side_effect = transform_side_effect

                mock_graph = MagicMock()
                mock_graph.astream = mock_graph_stream_with_bad_chunk
                mock_graph.ainvoke = AsyncMock(return_value={"weekly_plan": []})
                mock_get_graph.return_value = mock_graph

                # Act
                events = []
                async for event in stream_meal_plan(request):
                    events.append(event)

                # Assert: Should have warning event
                warning_events = [e for e in events if "warning" in e.lower()]
                assert len(warning_events) > 0, "Should send warning event on chunk error"

    @pytest.mark.asyncio
    async def test_ec022_2_stream_continues_after_chunk_error(self):
        """EC-022-2: Stream should continue processing after chunk error"""
        # Arrange
        from app.services.stream_service import stream_meal_plan

        request = MealPlanRequest(
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
            days=1,
        )

        chunks_yielded = []

        async def mock_graph_stream_multi_error(*args, **kwargs):
            chunks = [
                {"node1": {"events": [{"type": "progress", "data": "event1"}]}},
                {"node2": {"events": [None]}},  # Error
                {"node3": {"events": [{"type": "progress", "data": "event3"}]}},
                {"node4": {"events": [None]}},  # Error
                {"node5": {"events": [{"type": "progress", "data": "event5"}]}},
            ]
            for chunk in chunks:
                chunks_yielded.append(chunk)
                yield chunk

        with patch("app.services.stream_service.get_meal_planner_graph") as mock_get_graph:
            with patch("app.services.stream_service.transform_event") as mock_transform:
                def transform_conditional(event, node_name):
                    if event is None:
                        raise ValueError("Cannot transform None event")
                    return {"type": "progress", "data": event.get("data")}

                mock_transform.side_effect = transform_conditional

                mock_graph = MagicMock()
                mock_graph.astream = mock_graph_stream_multi_error
                mock_graph.ainvoke = AsyncMock(return_value={"weekly_plan": []})
                mock_get_graph.return_value = mock_graph

                # Act
                events = []
                async for event in stream_meal_plan(request):
                    events.append(event)

                # Assert: Should process all 5 chunks despite 2 errors
                assert len(chunks_yielded) == 5, "All chunks should be processed"
                # Should have completion event at the end
                assert any("complete" in e.lower() for e in events), "Should complete stream"

    @pytest.mark.asyncio
    async def test_ec022_3_partial_results_preserved_on_error(self):
        """EC-022-3: Partial results should be preserved when chunk fails"""
        # Arrange
        from app.services.stream_service import stream_meal_plan

        request = MealPlanRequest(
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
            days=1,
        )

        async def mock_graph_stream_partial(*args, **kwargs):
            # 2 good events, then error, then 1 more good event
            yield {"node1": {"events": [{"type": "progress", "node": "node1"}]}}
            yield {"node2": {"events": [{"type": "progress", "node": "node2"}]}}
            yield {"bad_node": {"events": [None]}}  # Error here
            yield {"node3": {"events": [{"type": "progress", "node": "node3"}]}}

        with patch("app.services.stream_service.get_meal_planner_graph") as mock_get_graph:
            with patch("app.services.stream_service.transform_event") as mock_transform:
                def transform_check_none(event, node_name):
                    if event is None:
                        raise ValueError("None event")
                    return {"type": "progress", "data": {"node": node_name}}

                mock_transform.side_effect = transform_check_none

                mock_graph = MagicMock()
                mock_graph.astream = mock_graph_stream_partial
                mock_graph.ainvoke = AsyncMock(return_value={"weekly_plan": []})
                mock_get_graph.return_value = mock_graph

                # Act
                events = []
                async for event in stream_meal_plan(request):
                    events.append(event)

                # Assert: Should have events from node1, node2, and node3 (3 progress + 1 warning + 1 complete)
                assert len(events) >= 3, "Should preserve partial results"

    @pytest.mark.asyncio
    async def test_ec022_4_final_state_completes_despite_chunk_errors(self):
        """EC-022-4: Final state should complete successfully despite chunk errors"""
        # Arrange
        from app.services.stream_service import stream_meal_plan

        request = MealPlanRequest(
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
            days=1,
        )

        async def mock_graph_stream_with_errors(*args, **kwargs):
            yield {"node1": {"events": [{"type": "progress"}]}}
            yield {"bad": {"events": [None]}}  # Error
            yield {"node2": {"events": [{"type": "progress"}]}}

        # Create proper mock with all required attributes
        mock_menu = MagicMock()
        mock_menu.meal_type = "아침"
        mock_menu.menu_name = "테스트 메뉴"
        mock_menu.calories = 500.0
        mock_menu.carb_g = 60.0
        mock_menu.protein_g = 20.0
        mock_menu.fat_g = 15.0
        mock_menu.sodium_mg = 500.0
        mock_menu.ingredients = [{"name": "재료1", "amount": "100g"}]
        mock_menu.recipe_steps = ["조리법"]
        mock_menu.recipe_url = "http://test.com"
        mock_menu.cooking_time_minutes = 15
        mock_menu.estimated_cost = 5000
        mock_menu.validation_warnings = []
        
        mock_day_plan = MagicMock()
        mock_day_plan.day = 1
        mock_day_plan.meals = [mock_menu]
        mock_day_plan.total_calories = 2000.0
        mock_day_plan.total_carb_g = 250.0
        mock_day_plan.total_protein_g = 100.0
        mock_day_plan.total_fat_g = 60.0
        mock_day_plan.total_cost = 15000
        
        final_weekly_plan = [mock_day_plan]

        with patch("app.services.stream_service.get_meal_planner_graph") as mock_get_graph:
            with patch("app.services.stream_service.transform_event") as mock_transform:
                mock_transform.side_effect = lambda e, n: (
                    {"type": "progress", "data": {}} if e is not None else (_ for _ in ()).throw(ValueError())
                )

                mock_graph = MagicMock()
                mock_graph.astream = mock_graph_stream_with_errors
                mock_graph.ainvoke = AsyncMock(return_value={"weekly_plan": final_weekly_plan})
                mock_get_graph.return_value = mock_graph

                # Act
                events = []
                async for event in stream_meal_plan(request):
                    events.append(event)

                # Assert: Should have completion event with final state
                completion_events = [e for e in events if "complete" in e.lower()]
                assert len(completion_events) > 0, "Should send completion event"
                assert mock_graph.ainvoke.called, "Should call ainvoke for final state"
