"""
API Health Check Tests

Health endpoint 테스트:
- API-HEALTH-001: Health check 정상 동작
- API-HEALTH-002: Health check 성능
"""

import pytest
import time


class TestHealthCheck:
    """Health Check Endpoint 테스트"""

    @pytest.mark.asyncio
    async def test_health001_basic_functionality(self, api_client):
        """API-HEALTH-001: Health check 정상 동작 확인"""
        # Act
        response = await api_client.get("/api/health")

        # Assert: Status code
        assert response.status_code == 200, "Health check should return 200 OK"

        # Assert: Response structure
        data = response.json()
        assert "status" in data, "Response should have 'status' field"
        assert "version" in data, "Response should have 'version' field"

        # Assert: status value
        assert data["status"] == "ok", "Status should be 'ok'"

        # Assert: version exists and is non-empty
        assert isinstance(data["version"], str), "Version should be string"
        assert len(data["version"]) > 0, "Version should not be empty"

    @pytest.mark.asyncio
    async def test_health002_performance(self, api_client):
        """API-HEALTH-002: Health check 성능 - 빠른 응답 (<100ms)"""
        # Measure response time
        start_time = time.time()

        response = await api_client.get("/api/health")

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        # Assert: Fast response (<100ms)
        assert elapsed_ms < 100, \
            f"Health check should respond in <100ms, got {elapsed_ms:.2f}ms"

        # Assert: Success
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health003_multiple_concurrent_requests(self, api_client):
        """API-HEALTH-003: 동시 다중 요청 처리"""
        import asyncio

        # Send 10 concurrent health check requests
        tasks = [
            api_client.get("/api/health")
            for _ in range(10)
        ]

        # Wait for all to complete
        responses = await asyncio.gather(*tasks)

        # Assert: All requests succeed
        assert len(responses) == 10, "Should handle 10 concurrent requests"
        for response in responses:
            assert response.status_code == 200, "All health checks should succeed"
            data = response.json()
            assert data["status"] == "ok"
