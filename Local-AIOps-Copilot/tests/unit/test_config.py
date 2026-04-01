"""Tests for shared configuration."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from shared.config.settings import (
    EnvironmentMode,
    LLMBackendType,
    Settings,
)


def test_default_settings():
    s = Settings(
        _env_file=None,  # Don't read .env in tests
    )
    assert s.environment == EnvironmentMode.DEV
    assert s.llm_backend == LLMBackendType.MOCK
    assert s.api_gateway_port == 8080
    assert s.agent_service_port == 50051


def test_gpu_mode():
    s = Settings(environment="gpu", _env_file=None)
    assert s.is_gpu_mode is True
    assert s.default_llm_backend == LLMBackendType.VLLM


def test_dev_mode_not_gpu():
    s = Settings(environment="dev", _env_file=None)
    assert s.is_gpu_mode is False


def test_backend_override():
    s = Settings(llm_backend="triton", _env_file=None)
    assert s.llm_backend == LLMBackendType.TRITON


def test_all_backend_types_valid():
    for backend in LLMBackendType:
        s = Settings(llm_backend=backend.value, _env_file=None)
        assert s.llm_backend == backend
