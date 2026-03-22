"""
Tests for the document service helpers.
"""

from app.rag.ingestion import SUPPORTED_EXTENSIONS


def test_supported_extensions_include_common_types():
    """Verify the expected file types are supported."""
    for ext in [".txt", ".md", ".pdf", ".docx"]:
        assert ext in SUPPORTED_EXTENSIONS
