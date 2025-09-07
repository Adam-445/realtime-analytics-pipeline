from enum import Enum


class Environment(str, Enum):
    """Application environment types."""

    PRODUCTION = "production"
    STAGING = "staging"
    TESTING = "testing"
    DEVELOPMENT = "development"

    @classmethod
    def is_production(cls, env: str) -> bool:
        """Check if environment is production."""
        return env.lower() == cls.PRODUCTION.value

    @classmethod
    def is_testing(cls, env: str) -> bool:
        """Check if environment is testing."""
        return env.lower() == cls.TESTING.value

    @classmethod
    def is_development(cls, env: str) -> bool:
        """Check if environment is development"""
        return env.lower() == cls.DEVELOPMENT.value
