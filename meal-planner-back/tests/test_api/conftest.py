"""
Shared fixtures for API testing

Provides reusable fixtures for API tests including:
- API client (httpx.AsyncClient with ASGITransport)
- Request builders (standard_request, request_builder)
- SSE event collectors
- Mock LLM service
"""

import pytest
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app


@pytest.fixture(scope="function")
async def api_client():
    """재사용 가능한 HTTP client (ASGI transport)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def standard_request():
    """표준 유효 요청 (다이어트, 7일 3끼)"""
    return {
        "goal": "다이어트",
        "weight": 70.0,
        "height": 175.0,
        "age": 30,
        "gender": "male",
        "activity_level": "moderate",
        "restrictions": [],
        "health_conditions": [],
        "budget": 100_000,
        "budget_type": "weekly",
        "cooking_time": "30분 이내",
        "skill_level": "중급",
        "meals_per_day": 3,
        "days": 7,
    }


@pytest.fixture
def minimal_request():
    """최소 유효 요청 (1일 1끼)"""
    return {
        "goal": "유지",
        "weight": 70.0,
        "height": 170.0,
        "age": 30,
        "gender": "male",
        "activity_level": "moderate",
        "budget": 20_000,
        "budget_type": "weekly",
        "cooking_time": "30분 이내",
        "skill_level": "중급",
        "meals_per_day": 1,
        "days": 1,
    }


@pytest.fixture
def request_builder(standard_request):
    """요청 변형 factory - 특정 필드만 override"""
    def build(**overrides):
        request = standard_request.copy()
        request.update(overrides)
        return request
    return build


@pytest.fixture
def sse_event_collector():
    """SSE 이벤트 수집 헬퍼 (async generator)"""
    async def collect(response):
        """
        SSE 응답에서 이벤트 파싱 및 수집

        Args:
            response: httpx.Response (streaming)

        Returns:
            List[dict]: 파싱된 SSE 이벤트 리스트
        """
        events = []
        async for line in response.aiter_lines():
            if line.startswith("data:"):
                try:
                    event_data = json.loads(line[5:])  # Remove 'data:' prefix
                    events.append(event_data)
                except json.JSONDecodeError:
                    # Skip invalid JSON
                    continue
        return events
    return collect


@pytest.fixture
def mock_llm_nutritionist():
    """Nutritionist agent용 deterministic LLM mock"""
    return json.dumps({
        "calories_target": 2000.0,
        "carb_ratio": 50,
        "protein_ratio": 30,
        "fat_ratio": 20,
        "reasoning": "다이어트 목표에 맞는 균형 잡힌 영양 비율",
    })


@pytest.fixture
def mock_llm_chef():
    """Chef agent용 deterministic LLM mock"""
    return json.dumps({
        "menu_name": "닭가슴살 현미밥",
        "ingredients": [
            {"name": "닭가슴살", "amount": "150g", "amount_g": 150.0},
            {"name": "현미밥", "amount": "210g", "amount_g": 210.0},
            {"name": "브로콜리", "amount": "100g", "amount_g": 100.0},
        ],
        "estimated_calories": 550.0,
        "estimated_cost": 5000,
        "cooking_time_minutes": 20,
        "reasoning": "고단백 저지방 메뉴",
    })


@pytest.fixture
def mock_llm_budget():
    """Budget agent용 deterministic LLM mock"""
    return json.dumps({
        "menu_name": "닭가슴살 현미밥",
        "ingredients": [
            {"name": "닭가슴살", "amount": "150g", "amount_g": 150.0},
            {"name": "현미밥", "amount": "210g", "amount_g": 210.0},
            {"name": "브로콜리", "amount": "100g", "amount_g": 100.0},
        ],
        "estimated_calories": 550.0,
        "estimated_cost": 4500,  # Adjusted cost
        "cooking_time_minutes": 20,
        "reasoning": "예산 범위 내 조정",
    })


@pytest.fixture
def mock_llm_service():
    """
    LLM Service mock (no-op)

    API 테스트는 LLM 통합 없이 API 레벨만 테스트합니다.
    실제 LLM 통합 테스트는 edge case 테스트에서 수행됩니다.
    """
    # No-op - API tests focus on API layer only
    yield


@pytest.fixture
def event_types_counter():
    """SSE 이벤트 타입별 카운트 헬퍼"""
    def count(events):
        """
        이벤트 타입별 카운트

        Args:
            events: List[dict] - SSE 이벤트 리스트

        Returns:
            dict: {"progress": 3, "validation": 5, ...}
        """
        counts = {}
        for event in events:
            event_type = event.get("type")
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts
    return count


@pytest.fixture
def validation_results_extractor():
    """Validation 이벤트에서 결과 추출 헬퍼"""
    def extract(events):
        """
        Validation 이벤트에서 passed 결과 추출

        Args:
            events: List[dict] - SSE 이벤트 리스트

        Returns:
            dict: {"nutrition_checker": True, "allergy_checker": True, ...}
        """
        results = {}
        for event in events:
            if event.get("type") == "validation":
                data = event.get("data", {})
                validator = data.get("validator")
                passed = data.get("passed")
                results[validator] = passed
        return results
    return extract
