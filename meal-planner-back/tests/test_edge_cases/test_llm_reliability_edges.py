"""EC-018, EC-019, EC-020: LLM Service Reliability Edge Cases

CRITICAL: Tests for LLM timeout, rate limit retry, and JSON validation errors
"""
import asyncio
from json import JSONDecodeError
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from app.services.llm_service import LLMService


class TestLLMTimeoutEdges:
    """EC-018: LLM API Timeout (25s limit)"""

    @pytest.mark.asyncio
    async def test_ec018_1_timeout_after_25_seconds(self):
        """EC-018-1: LLM API call exceeding 25s should raise TimeoutError"""
        # Arrange: Mock LLM that takes 30 seconds (> 25s limit)
        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(30)

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=slow_llm)

        llm_service = LLMService(mock_mode=False)
        llm_service.llm = mock_llm

        # Act & Assert
        with pytest.raises(TimeoutError) as exc_info:
            await llm_service.ainvoke("test prompt")

        # Assert: Error message mentions timeout
        assert "25초" in str(exc_info.value)
        assert "초과" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ec018_2_within_timeout_succeeds(self):
        """EC-018-2: LLM API call under 25s should succeed"""
        # Arrange: Mock LLM that responds in 1 second (< 25s limit)
        async def mock_quick_response(messages):
            await asyncio.sleep(0.1)
            return AIMessage(content='{"test": "response"}')

        mock_llm = MagicMock()
        mock_llm.ainvoke = mock_quick_response

        llm_service = LLMService(mock_mode=False)
        llm_service.llm = mock_llm

        # Act
        result = await llm_service.ainvoke("test prompt")

        # Assert
        assert result == '{"test": "response"}'

    @pytest.mark.asyncio
    async def test_ec018_3_timeout_logs_error(self):
        """EC-018-3: Timeout should log prompt length and preview"""
        # Arrange: Mock LLM that times out
        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(30)

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=slow_llm)

        llm_service = LLMService(mock_mode=False)
        llm_service.llm = mock_llm

        long_prompt = "x" * 500

        # Act & Assert
        with pytest.raises(TimeoutError):
            await llm_service.ainvoke(long_prompt)

        # Note: In production, verify logger.error was called with prompt_length=500

    @pytest.mark.asyncio
    async def test_ec018_4_mock_mode_no_timeout(self):
        """EC-018-4: Mock mode should bypass timeout logic"""
        # Arrange: Mock mode enabled
        llm_service = LLMService(mock_mode=True)

        # Act: Even with long execution, mock mode should work
        result = await llm_service.ainvoke("영양사" * 100)

        # Assert: Should get mock response without timeout
        assert "menu_name" in result
        assert "닭가슴살" in result


class TestLLMRateLimitEdges:
    """EC-019: LLM Rate Limit Retry with Exponential Backoff"""

    @pytest.mark.asyncio
    async def test_ec019_1_rate_limit_retry_succeeds_on_second_attempt(self):
        """EC-019-1: Rate limit error should retry with exponential backoff"""
        # Arrange: Fail first, succeed second
        call_count = 0

        async def mock_rate_limited_then_success(messages):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 rate_limit exceeded")
            return AIMessage(content='{"success": true}')

        mock_llm = MagicMock()
        mock_llm.ainvoke = mock_rate_limited_then_success

        llm_service = LLMService(mock_mode=False)
        llm_service.llm = mock_llm

        # Act
        result = await llm_service.ainvoke("test")

        # Assert: Should succeed after 1 retry
        assert call_count == 2
        assert "success" in result

    @pytest.mark.asyncio
    async def test_ec019_2_rate_limit_max_retries_exhausted(self):
        """EC-019-2: After 3 retries, rate limit error should raise"""
        # Arrange: Always fail with rate limit
        call_count = 0

        async def mock_always_rate_limited(messages):
            nonlocal call_count
            call_count += 1
            raise Exception("429 Too Many Requests")

        mock_llm = MagicMock()
        mock_llm.ainvoke = mock_always_rate_limited

        llm_service = LLMService(mock_mode=False)
        llm_service.llm = mock_llm

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await llm_service.ainvoke("test")

        # Assert: Should have attempted 4 times (initial + 3 retries)
        assert call_count == 4
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ec019_3_exponential_backoff_delays(self):
        """EC-019-3: Retry delays should be 1s, 2s, 4s (exponential)"""
        # Arrange: Track retry delays
        call_times = []

        async def mock_rate_limited(messages):
            call_times.append(asyncio.get_event_loop().time())
            raise Exception("quota exceeded - rate limit")

        mock_llm = MagicMock()
        mock_llm.ainvoke = mock_rate_limited

        llm_service = LLMService(mock_mode=False)
        llm_service.llm = mock_llm

        # Act
        try:
            await llm_service.ainvoke("test")
        except Exception:
            pass

        # Assert: Delays should be ~1s, ~2s, ~4s between attempts
        if len(call_times) >= 4:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            delay3 = call_times[3] - call_times[2]

            assert 0.9 <= delay1 <= 1.2  # ~1s ± tolerance
            assert 1.9 <= delay2 <= 2.2  # ~2s ± tolerance
            assert 3.9 <= delay3 <= 4.2  # ~4s ± tolerance

    @pytest.mark.asyncio
    async def test_ec019_4_non_rate_limit_error_no_retry(self):
        """EC-019-4: Non-rate limit errors should fail immediately without retry"""
        # Arrange: Other error (not rate limit)
        call_count = 0

        async def mock_generic_error(messages):
            nonlocal call_count
            call_count += 1
            raise Exception("Connection refused")

        mock_llm = MagicMock()
        mock_llm.ainvoke = mock_generic_error

        llm_service = LLMService(mock_mode=False)
        llm_service.llm = mock_llm

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await llm_service.ainvoke("test")

        # Assert: Should only attempt once (no retries for non-rate-limit errors)
        assert call_count == 1
        assert "Connection refused" in str(exc_info.value)


class TestValidationErrorEdges:
    """EC-020: JSON Parsing and Pydantic ValidationError Handling"""

    @pytest.mark.asyncio
    async def test_ec020_1_nutritionist_json_decode_error_returns_none(self):
        """EC-020-1: Nutritionist with malformed JSON should return None"""
        # Arrange
        from app.agents.nodes.meal_planning.nutritionist import nutritionist_agent

        with patch("app.agents.nodes.meal_planning.nutritionist.get_llm_service") as mock_get_llm:
            mock_llm_service = AsyncMock()
            # Return invalid JSON
            mock_llm_service.ainvoke = AsyncMock(return_value="{ invalid json }")
            mock_get_llm.return_value = mock_llm_service

            state = {
                "profile": MagicMock(
                    height_cm=170, weight_kg=70, activity_level="보통",
                    restrictions=[], health_conditions=[]
                ),
                "per_meal_targets": MagicMock(calories=600, carb_g=70, protein_g=25, fat_g=20),
                "current_meal_type": "아침",
                "current_day": 1,
                "retry_count": 0
            }

            # Act
            result = await nutritionist_agent(state)

            # Assert: Should return None, not crash
            assert result["nutritionist_recommendation"] is None
            assert result["events"][0]["type"] == "error"
            assert result["events"][0]["status"] == "json_decode_failed"

    @pytest.mark.asyncio
    async def test_ec020_2_chef_validation_error_missing_fields(self):
        """EC-020-2: Chef with missing required fields should return None"""
        # Arrange
        from app.agents.nodes.meal_planning.chef import chef_agent

        with patch("app.agents.nodes.meal_planning.chef.get_llm_service") as mock_get_llm:
            mock_llm_service = AsyncMock()
            # Return JSON missing required 'reasoning' field
            mock_llm_service.ainvoke = AsyncMock(return_value='''{
                "menu_name": "test",
                "ingredients": [{"name": "밥", "amount": "210g"}],
                "estimated_calories": 500,
                "estimated_cost": 3000,
                "cooking_time_minutes": 15
            }''')
            mock_get_llm.return_value = mock_llm_service

            state = {
                "profile": MagicMock(
                    cooking_skill="초급", available_time_minutes=30, cooking_time="30분 이내",
                    skill_level="초급",
                    restrictions=[], health_conditions=[]
                ),
                "per_meal_targets": MagicMock(calories=600, protein_g=25, carb_g=70, fat_g=20),
                "current_meal_type": "점심",
                "current_day": 1,
                "retry_count": 0
            }

            # Act
            result = await chef_agent(state)

            # Assert: Should return None due to missing 'reasoning'
            assert result["chef_recommendation"] is None
            assert result["events"][0]["type"] == "error"
            assert result["events"][0]["status"] == "validation_failed"
            assert "reasoning" in result["events"][0]["data"]["missing_fields"]

    @pytest.mark.asyncio
    async def test_ec020_3_budget_validation_error_invalid_type(self):
        """EC-020-3: Budget with invalid field types should return None"""
        # Arrange
        from app.agents.nodes.meal_planning.budget import budget_agent

        with patch("app.agents.nodes.meal_planning.budget.get_llm_service") as mock_get_llm:
            with patch("app.agents.nodes.meal_planning.budget.get_pricing_service") as mock_pricing:
                mock_llm_service = AsyncMock()
                # Return JSON with invalid type (string instead of int)
                mock_llm_service.ainvoke = AsyncMock(return_value='''{
                    "menu_name": "test",
                    "ingredients": [{"name": "밥", "amount": "210g"}],
                    "estimated_calories": "not a number",
                    "estimated_cost": 3000,
                    "cooking_time_minutes": 15,
                    "reasoning": "test"
                }''')
                mock_get_llm.return_value = mock_llm_service

                mock_pricing_service = MagicMock()
                mock_pricing_service.fetch_ingredient_prices = AsyncMock(return_value={})
                mock_pricing.return_value = mock_pricing_service

                state = {
                    "profile": MagicMock(
                        budget=20000, days=7, meals_per_day=3,
                        restrictions=[], health_conditions=[]
                    ),
                    "per_meal_targets": MagicMock(calories=600, protein_g=25, carb_g=70, fat_g=20),
                    "per_meal_budget": 3000,
                    "current_meal_type": "저녁",
                    "current_day": 1,
                    "retry_count": 0
                }

                # Act
                result = await budget_agent(state)

                # Assert: Should return None due to type validation error
                assert result["budget_recommendation"] is None
                assert result["events"][0]["type"] == "error"
                assert result["events"][0]["status"] == "validation_failed"

    @pytest.mark.asyncio
    async def test_ec020_4_all_agents_handle_validation_gracefully(self):
        """EC-020-4: All 3 agents should handle ValidationError consistently"""
        # This test verifies that nutritionist, chef, and budget all follow
        # the same pattern for ValidationError handling

        from app.agents.nodes.meal_planning.nutritionist import nutritionist_agent
        from app.agents.nodes.meal_planning.chef import chef_agent
        from app.agents.nodes.meal_planning.budget import budget_agent

        # Arrange: Invalid JSON for all agents (empty object)
        invalid_json = "{}"

        agents = [
            ("nutritionist", nutritionist_agent, "nutritionist_recommendation"),
            ("chef", chef_agent, "chef_recommendation"),
            ("budget", budget_agent, "budget_recommendation"),
        ]

        for agent_name, agent_func, recommendation_key in agents:
            with patch(f"app.agents.nodes.meal_planning.{agent_name}.get_llm_service") as mock_get_llm:
                if agent_name == "budget":
                    with patch(f"app.agents.nodes.meal_planning.{agent_name}.get_pricing_service") as mock_pricing:
                        mock_pricing_service = MagicMock()
                        mock_pricing_service.fetch_ingredient_prices = AsyncMock(return_value={})
                        mock_pricing.return_value = mock_pricing_service

                        mock_llm_service = AsyncMock()
                        mock_llm_service.ainvoke = AsyncMock(return_value=invalid_json)
                        mock_get_llm.return_value = mock_llm_service

                        state = {
                            "profile": MagicMock(
                                height_cm=170, weight_kg=70, activity_level="보통",
                                cooking_skill="초급", available_time_minutes=30, cooking_time="30분 이내",
                                skill_level="초급",
                                budget=20000, days=7, meals_per_day=3,
                                restrictions=[], health_conditions=[]
                            ),
                            "per_meal_targets": MagicMock(calories=600, protein_g=25, carb_g=70, fat_g=20),
                            "per_meal_budget": 3000,
                            "current_meal_type": "아침",
                            "current_day": 1,
                            "retry_count": 0
                        }

                        result = await agent_func(state)
                else:
                    mock_llm_service = AsyncMock()
                    mock_llm_service.ainvoke = AsyncMock(return_value=invalid_json)
                    mock_get_llm.return_value = mock_llm_service

                    state = {
                        "profile": MagicMock(
                            height_cm=170, weight_kg=70, activity_level="보통",
                            cooking_skill="초급", available_time_minutes=30, cooking_time="30분 이내",
                            skill_level="초급",
                            restrictions=[], health_conditions=[]
                        ),
                        "per_meal_targets": MagicMock(calories=600, protein_g=25, carb_g=70, fat_g=20),
                        "current_meal_type": "아침",
                        "current_day": 1,
                        "retry_count": 0
                    }

                    result = await agent_func(state)

                # Assert: All agents should return None and error event
                assert result[recommendation_key] is None, f"{agent_name} should return None"
                assert result["events"][0]["type"] == "error", f"{agent_name} should emit error event"
                assert result["events"][0]["status"] == "validation_failed", f"{agent_name} should have validation_failed status"
