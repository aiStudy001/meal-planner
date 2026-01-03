"""
API Error Response Tests (Simplified)

API 레벨 에러만 테스트:
- API-ERR-001: Validation 에러 (422)
- API-ERR-002: 잘못된 메소드 (405)

Note: LLM timeout, graph error 등은 test_edge_cases에서 검증
"""

import pytest


class TestErrorResponses:
    """API 에러 응답 테스트 (API 레벨만)"""

    @pytest.mark.asyncio
    async def test_err001_validation_errors(
        self, api_client, request_builder
    ):
        """API-ERR-001: Validation 에러 (422)"""
        # 예산 부족
        invalid_request = request_builder(
            budget=40_000,
            meals_per_day=3,
            days=7
        )

        response = await api_client.post(
            "/api/generate",
            json=invalid_request,
            timeout=5.0
        )

        # Should return 422
        assert response.status_code == 422

        # Should have detail
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_err002_wrong_method_not_allowed(self, api_client):
        """API-ERR-002: 잘못된 HTTP 메소드 (405)"""
        # GET on /api/generate should fail (requires POST)
        response = await api_client.get("/api/generate")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_err003_missing_required_fields(self, api_client):
        """API-ERR-003: 필수 필드 누락 (422)"""
        # Empty request
        response = await api_client.post(
            "/api/generate",
            json={},
            timeout=5.0
        )

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
