"""
Tests for core configuration loading.
"""

from app.core.config import Settings, PROJECT_ROOT


def test_default_settings():
    """Settings class defaults are sensible even without any .env file."""
    # _env_file=None prevents pydantic-settings from reading the .env,
    # so we test only the hard-coded defaults in the class definition.
    s = Settings(_env_file=None)
    assert s.llm_provider == "huggingface"
    assert s.qdrant_port == 6333
    assert s.chunk_size == 512
    assert s.chunk_overlap == 50
    assert s.app_port == 8000


def test_upload_path_is_absolute():
    """The upload_path property should return an absolute Path."""
    s = Settings(_env_file=None)
    assert s.upload_path.is_absolute()


def test_project_root_exists():
    """PROJECT_ROOT should point at a real directory containing requirements.txt."""
    assert PROJECT_ROOT.is_dir()
    assert (PROJECT_ROOT / "requirements.txt").is_file()
