"""Helpers shared by the test suites."""

from typing import Any

from app.presentation.settings import Settings


def build_settings(**overrides: Any) -> Settings:
    """Settings for a test, ignoring any .env in the working tree."""
    return Settings(**{"_env_file": None, **overrides})
