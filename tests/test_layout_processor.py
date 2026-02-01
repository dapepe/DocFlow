"""
Test suite for LayoutProcessor.

Tests cover:
- Layout extraction from different file types
- Element detection (text, tables, figures)
- Bounding box calculations
- Reading order computation
- Section detection
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from docflow.layout_processor import (
    LayoutProcessor,
    LayoutElement,
    BoundingBox,
    extract_layout,
)


class TestBoundingBox:
    """Test BoundingBox dataclass."""

    def test_bbox_creation(self):
        """Test bounding box creation."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200, page=1)

        assert bbox.x0 == 10
        assert bbox.y0 == 20
        assert bbox.x1 == 100
        assert bbox.y1 == 200
        assert bbox.page == 1

    def test_bbox_to_dict(self):
        """Test bounding box serialization."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200, page=1)
        d = bbox.to_dict()

        assert d["x0"] == 10
        assert d["y0"] == 20
        assert d["width"] == 90
        assert d["height"] == 180
        assert d["page"] == 1

    def test_bbox_repr(self):
        """Test bounding box string representation."""
        bbox = BoundingBox(x0=10.5, y0=20.5, x1=100.5, y1=200.5, page=2)
        repr_str = repr(bbox)

        assert "BBox" in repr_str
        assert "p2" in repr_str


class TestLayoutElement:
    """Test LayoutElement dataclass."""

    def test_element_creation(self):
        """Test layout element creation."""
        bbox = BoundingBox(0, 0, 100, 50, 1)
        element = LayoutElement(
            element_type="text", bbox=bbox, content="Hello World", confidence=0.95
        )

        assert element.element_type == "text"
        assert element.content == "Hello World"
        assert element.confidence == 0.95

    def test_element_to_dict(self):
        """Test layout element serialization."""
        bbox = BoundingBox(0, 0, 100, 50, 1)
        element = LayoutElement(
            element_type="text", bbox=bbox, content="Hello", metadata={"font_size": 12}
        )

        d = element.to_dict()
        assert d["type"] == "text"
        assert d["content"] == "Hello"
        assert d["metadata"]["font_size"] == 12


class TestLayoutProcessor:
    """Test LayoutProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create a LayoutProcessor instance."""
        return LayoutProcessor()

    def test_processor_initialization(self, processor):
        """Test processor initializes correctly."""
        assert processor.elements == []

    def test_extract_layout_unsupported_file(self, processor):
        """Test handling of unsupported file types."""
        with pytest.raises(ValueError):
            processor.extract_layout("/path/to/file.xyz")

    def test_extract_layout_missing_file(self, processor):
        """Test handling of missing files."""
        with pytest.raises(FileNotFoundError):
            processor.extract_layout("/nonexistent/file.pdf")

    def test_group_words_into_lines(self, processor):
        """Test word grouping into lines."""
        words = [
            {"text": "Hello", "x0": 10, "x1": 50, "top": 100, "bottom": 120},
            {"text": "World", "x0": 60, "x1": 100, "top": 100, "bottom": 120},
            {"text": "Next", "x0": 10, "x1": 40, "top": 140, "bottom": 160},
        ]

        lines = processor._group_words_into_lines(words)

        assert len(lines) == 2
        assert lines[0]["text"] == "Hello World"
        assert lines[1]["text"] == "Next"

    def test_compute_reading_order(self, processor):
        """Test reading order computation."""
        elements = [
            LayoutElement("text", BoundingBox(0, 100, 100, 120, 1), "Second"),
            LayoutElement("text", BoundingBox(0, 50, 100, 70, 1), "First"),
            LayoutElement("text", BoundingBox(0, 150, 100, 170, 2), "Third"),
        ]

        ordered = processor._compute_reading_order(elements)

        assert ordered[0].content == "First"
        assert ordered[1].content == "Second"
        assert ordered[2].content == "Third"

    def test_detect_sections_with_headings(self, processor):
        """Test section detection from headings."""
        elements = [
            LayoutElement(
                "text",
                BoundingBox(0, 0, 100, 20, 1),
                "INTRODUCTION",
                metadata={"font_size": 16},
            ),
            LayoutElement("text", BoundingBox(0, 30, 100, 50, 1), "Some content"),
            LayoutElement(
                "text",
                BoundingBox(0, 60, 100, 80, 1),
                "CONCLUSION",
                metadata={"font_size": 16},
            ),
            LayoutElement("text", BoundingBox(0, 90, 100, 110, 1), "More content"),
        ]

        sections = processor._detect_sections(elements)

        assert len(sections) == 2
        assert sections[0]["heading"] == "INTRODUCTION"
        assert sections[1]["heading"] == "CONCLUSION"


class TestExtractLayout:
    """Test extract_layout convenience function."""

    def test_extract_layout_function(self):
        """Test the convenience function."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            layout = extract_layout(tmp_path)

            assert "elements" in layout
            assert "metadata" in layout
            assert layout["metadata"]["format"] in ["JPEG", "PNG", None]
        finally:
            os.unlink(tmp_path)


class TestPDFLayoutExtraction:
    """Test PDF-specific layout extraction."""

    def test_pdf_layout_structure(self, processor):
        """Test PDF layout returns expected structure."""
        # Create a minimal PDF for testing
        # Note: This is a simplified test - real PDF testing would need actual files

        mock_layout = {
            "sections": [],
            "tables": [],
            "figures": [],
            "elements": [],
            "reading_order": [],
            "metadata": {"total_pages": 1},
        }

        with patch.object(processor, "_extract_pdf_layout", return_value=mock_layout):
            result = processor.extract_layout("/fake/path.pdf")

            assert "sections" in result
            assert "tables" in result
            assert "figures" in result


class TestDOCXLayoutExtraction:
    """Test DOCX-specific layout extraction."""

    def test_docx_heading_detection(self, processor):
        """Test heading detection in DOCX."""
        elements = [
            LayoutElement(
                "text",
                BoundingBox(0, 0, 100, 12, 1),
                "Heading 1",
                metadata={"is_heading": True},
            ),
            LayoutElement(
                "text",
                BoundingBox(0, 24, 100, 36, 1),
                "Paragraph text",
                metadata={"is_heading": False},
            ),
        ]

        sections = processor._detect_sections_docx(elements)

        assert len(sections) == 1
        assert sections[0]["heading"] == "Heading 1"
        assert "Paragraph text" in sections[0]["content"]


class TestImageLayoutExtraction:
    """Test image-specific layout extraction."""

    def test_image_layout_returns_figure(self, processor):
        """Test image files return figure element."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            layout = processor.extract_layout(tmp_path)

            assert len(layout["elements"]) == 1
            assert layout["elements"][0]["type"] == "figure"
            assert "width" in layout["metadata"]
            assert "height" in layout["metadata"]
        finally:
            os.unlink(tmp_path)


class TestErrorHandling:
    """Test error handling in layout processor."""

    def test_pdfplumber_import_error(self, processor):
        """Test graceful handling when pdfplumber not available."""
        with patch.dict("sys.modules", {"pdfplumber": None}):
            # Should fall back to basic extraction
            mock_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            mock_pdf.close()

            try:
                result = processor.extract_layout(mock_pdf.name)
                # Should return basic structure even without pdfplumber
                assert "elements" in result or "error" in result
            finally:
                os.unlink(mock_pdf.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
