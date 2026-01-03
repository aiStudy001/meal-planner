"""
API SSE Sequence Tests (Simplified)

SSE 프로토콜 준수만 테스트:
- API-SSE-001: SSE 헤더 검증
- API-SSE-002: SSE 스트림 시작 확인

Note: 실제 이벤트 시퀀스 테스트는 test_edge_cases/test_e2e_edges.py에서 수행
"""

import pytest


class TestSSESequences:
    """SSE 프로토콜 테스트 (이벤트 내용 검증 제외)"""

    @pytest.mark.asyncio
    async def test_sse001_streaming_headers(
        self, api_client, minimal_request
    ):
        """API-SSE-001: SSE 헤더 검증"""
        response = await api_client.post(
            "/api/generate",
            json=minimal_request,
            timeout=5.0
        )

        # Assert: Status code
        assert response.status_code == 200

        # Assert: Content-Type
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    @pytest.mark.asyncio
    async def test_sse002_stream_starts(
        self, api_client, minimal_request
    ):
        """API-SSE-002: SSE 스트림 시작 확인"""
        response = await api_client.post(
            "/api/generate",
            json=minimal_request,
            timeout=5.0
        )

        # Should start streaming
        assert response.status_code == 200

        # Can iterate lines (even if we don't verify content)
        line_count = 0
        async for line in response.aiter_lines():
            line_count += 1
            if line_count >= 3:  # Just verify we can read stream
                break

        assert line_count >= 1, "Should receive at least one line from stream"
