"""EC-012: Conflict Resolver Edge Cases

CRITICAL: Tests for all recommendations None crash fix
"""
import pytest
from app.agents.nodes.meal_planning.conflict_resolver import conflict_resolver
from app.models.state import Menu


class TestConflictResolverEdges:
    """EC-012: All Recommendations None"""

    @pytest.mark.asyncio
    async def test_ec012_1_all_none_first_meal(self, empty_state):
        """EC-012-1: All recommendations None + current_menu None → emergency fallback"""
        # Arrange: 첫 끼니에 모든 전문가 실패
        empty_state["nutritionist_recommendation"] = None
        empty_state["chef_recommendation"] = None
        empty_state["budget_recommendation"] = None
        empty_state["current_menu"] = None
        empty_state["current_day"] = 1
        empty_state["current_meal_type"] = "아침"
        empty_state["retry_count"] = 0

        # Act
        result = await conflict_resolver(empty_state)

        # Assert: Emergency fallback menu 생성
        assert "current_menu" in result
        assert result["current_menu"] is not None
        assert isinstance(result["current_menu"], Menu)
        assert result["current_menu"].menu_name == "기본 식단 (재시도 필요)"
        assert len(result["current_menu"].ingredients) == 2  # 현미밥, 계란
        assert result["current_menu"].calories == 500

        # Assert: Error event 발생
        assert "events" in result
        assert len(result["events"]) > 0
        assert result["events"][0]["type"] == "error"
        assert result["events"][0]["status"] == "fallback"

    @pytest.mark.asyncio
    async def test_ec012_2_all_none_keep_previous(self, empty_state, mock_menu):
        """EC-012-2: All recommendations None + current_menu exists → keep previous"""
        # Arrange: 재시도 시나리오 - 이전 메뉴 존재
        empty_state["nutritionist_recommendation"] = None
        empty_state["chef_recommendation"] = None
        empty_state["budget_recommendation"] = None
        empty_state["current_menu"] = mock_menu
        empty_state["retry_count"] = 2

        # Act
        result = await conflict_resolver(empty_state)

        # Assert: 이전 메뉴 재사용
        assert "current_menu" in result
        assert result["current_menu"] == mock_menu
        assert result["current_menu"].menu_name == "테스트 메뉴"

        # Assert: Warning event 발생
        assert "events" in result
        assert result["events"][0]["type"] == "warning"
        assert result["events"][0]["status"] == "reused_previous"

    @pytest.mark.asyncio
    async def test_ec012_3_partial_none_with_previous(
        self, empty_state, mock_menu, mock_recommendation
    ):
        """EC-012-3: Some recommendations None → fill with previous menu data"""
        # Arrange: nutritionist만 성공, 나머지 실패
        empty_state["nutritionist_recommendation"] = mock_recommendation
        empty_state["chef_recommendation"] = None
        empty_state["budget_recommendation"] = None
        empty_state["current_menu"] = mock_menu

        # Act
        result = await conflict_resolver(empty_state)

        # Assert: 메뉴 생성 성공 (LLM이 nutritionist + 이전 메뉴 데이터 활용)
        assert "current_menu" in result
        assert result["current_menu"] is not None
        assert isinstance(result["current_menu"], Menu)

    @pytest.mark.asyncio
    async def test_ec012_4_all_recommendations_present(
        self, empty_state, mock_recommendation
    ):
        """EC-012-4: All recommendations present → normal conflict resolution"""
        # Arrange: 모든 전문가 정상 동작
        empty_state["nutritionist_recommendation"] = mock_recommendation
        empty_state["chef_recommendation"] = mock_recommendation
        empty_state["budget_recommendation"] = mock_recommendation

        # Act
        result = await conflict_resolver(empty_state)

        # Assert: 정상 메뉴 생성
        assert "current_menu" in result
        assert result["current_menu"] is not None
        assert isinstance(result["current_menu"], Menu)

        # Assert: Progress event 발생
        assert "events" in result
        assert result["events"][0]["type"] == "progress"
        assert result["events"][0]["status"] == "completed"
