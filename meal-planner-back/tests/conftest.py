"""Pytest 설정 파일"""
import os
import pytest
from dotenv import load_dotenv

# 테스트 환경 변수 로드
load_dotenv()

# 테스트 실행 시 MOCK_MODE 강제 활성화
os.environ["MOCK_MODE"] = "true"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """테스트 환경 설정"""
    # Mock 모드 확인
    assert os.getenv("MOCK_MODE", "false").lower() == "true", \
        "테스트는 MOCK_MODE=true에서만 실행되어야 합니다"

    yield

    # 테스트 종료 후 정리 (필요시)
    pass
