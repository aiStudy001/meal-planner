"""
API Contract Tests (Simplified)

Schema 안정성만 테스트:
- API-CT-001: Request Schema 안정성
- API-CT-002: Health Check Contract

Note: Response schema는 실제 응답 필요하므로 test_edge_cases에서 검증
"""

import pytest
from app.models.requests import MealPlanRequest


class TestAPIContract:
    """API Contract 테스트 - Schema 안정성"""

    def test_ct001_request_schema_stability(self, standard_request):
        """API-CT-001: Request Schema 안정성"""
        # Assert: standard_request는 유효한 MealPlanRequest여야 함
        try:
            request_obj = MealPlanRequest(**standard_request)
        except Exception as e:
            pytest.fail(f"Standard request should be valid MealPlanRequest: {e}")

        # Assert: 모든 필수 필드 존재
        required_fields = [
            "goal", "weight", "height", "age", "gender", "activity_level",
            "budget", "budget_type", "cooking_time", "skill_level",
            "meals_per_day", "days"
        ]
        for field in required_fields:
            assert hasattr(request_obj, field), \
                f"MealPlanRequest should have required field: {field}"

        # Assert: JSON schema 생성 가능
        schema = MealPlanRequest.model_json_schema()
        assert "properties" in schema
        assert "required" in schema

        # Assert: 주요 필드 타입 검증
        properties = schema["properties"]
        assert properties["goal"]["enum"] == ["다이어트", "벌크업", "유지", "질병관리"]
        assert properties["gender"]["enum"] == ["male", "female"]

    @pytest.mark.asyncio
    async def test_ct002_health_check_contract(self, api_client):
        """API-CT-002: Health Check Contract"""
        response = await api_client.get("/api/health")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["status"] == "ok"
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0
