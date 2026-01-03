"""EC-017: Configuration & Environment Edge Cases

CRITICAL: Tests for missing API key validation (fail-fast at startup)
"""
import pytest
from pydantic import ValidationError
from app.config import Settings


class TestConfigEdges:
    """EC-017: Missing API Key Validation"""

    def test_ec017_1_missing_api_key_production(self):
        """EC-017-1: MOCK_MODE=false without API key should raise ValueError"""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                MOCK_MODE=False,
                ANTHROPIC_API_KEY="",  # Empty string
            )

        # Assert: Error message should be clear
        assert "ANTHROPIC_API_KEY is required when MOCK_MODE=false" in str(
            exc_info.value
        )

    def test_ec017_2_missing_api_key_none_production(self):
        """EC-017-2: MOCK_MODE=false with API key=None should raise ValueError"""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                MOCK_MODE=False,
                ANTHROPIC_API_KEY=None,
            )

        # Assert
        assert "ANTHROPIC_API_KEY is required" in str(exc_info.value)

    def test_ec017_4_mock_mode_with_api_key(self):
        """EC-017-4: MOCK_MODE=true with API key should also work"""
        # Arrange & Act
        config = Settings(
            MOCK_MODE=True,
            ANTHROPIC_API_KEY="sk-test-key-123",
        )

        # Assert
        assert config.MOCK_MODE is True
        assert config.ANTHROPIC_API_KEY == "sk-test-key-123"

    def test_ec017_5_production_with_valid_api_key(self):
        """EC-017-5: MOCK_MODE=false with valid API key should succeed"""
        # Arrange & Act
        config = Settings(
            MOCK_MODE=False,
            ANTHROPIC_API_KEY="sk-ant-api03-valid-key-here",
        )

        # Assert
        assert config.MOCK_MODE is False
        assert config.ANTHROPIC_API_KEY.startswith("sk-ant-api")

    def test_ec017_6_default_mock_mode(self):
        """EC-017-6: Default MOCK_MODE should be False"""
        # Arrange & Act
        with pytest.raises(ValidationError):
            # Without explicit MOCK_MODE, defaults to False
            # So missing API key should fail
            Settings(ANTHROPIC_API_KEY="")

    def test_ec017_7_env_override_via_environment(self, monkeypatch):
        """EC-017-7: Settings should respect environment variables"""
        # Arrange: Set environment variables (takes precedence over .env file)
        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env-variable")

        # Act
        config = Settings()

        # Assert
        assert config.MOCK_MODE is False
        assert config.ANTHROPIC_API_KEY == "sk-from-env-variable"

    def test_ec017_8_validation_error_message_quality(self):
        """EC-017-8: Error message should guide user to solution"""
        # Arrange & Act
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                MOCK_MODE=False,
                ANTHROPIC_API_KEY=None,
            )

        error_message = str(exc_info.value)

        # Assert: Message should mention .env and MOCK_MODE
        assert ".env" in error_message or "MOCK_MODE" in error_message
        assert "testing" in error_message.lower()
