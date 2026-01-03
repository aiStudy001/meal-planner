"""
API Happy Path Tests (Simplified)

API 레벨 기본 동작만 테스트:
- API-HP-001: Health check 정상 동작
- API-HP-002: 유효한 요청 수락 (202 accepted)
- API-HP-003: 잘못된 엔드포인트 (404)

Note: 전체 워크플로우 테스트는 test_edge_cases/test_e2e_edges.py에서 수행
"""

import pytest


class TestHappyPaths:
    """API 기본 동작 테스트 (LLM 통합 없음)"""

    @pytest.mark.asyncio
    async def test_hp001_health_check_works(self, api_client):
        """API-HP-001: Health check 정상 동작"""
        response = await api_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_hp002_valid_request_accepted(
        self, api_client, standard_request
    ):
        """API-HP-002: 유효한 요청은 수락됨 (SSE 스트림 시작)"""
        response = await api_client.post(
            "/api/generate",
            json=standard_request,
            timeout=5.0
        )

        # Should accept and start SSE stream
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_hp003_invalid_endpoint_404(self, api_client):
        """API-HP-003: 잘못된 엔드포인트는 404"""
        response = await api_client.get("/api/invalid_endpoint")

        assert response.status_code == 404
