"""
Layout-Aware Document Processing

Extracts document structure, not just text.
Identifies sections, tables, figures, and their spatial relationships.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """Represents a rectangular region in a document."""

    x0: float  # Left coordinate
    y0: float  # Top coordinate
    x1: float  # Right coordinate
    y1: float  # Bottom coordinate
    page: int = 1  # Page number

    def __repr__(self) -> str:
        return f"BBox({self.x0:.1f}, {self.y0:.1f}, {self.x1:.1f}, {self.y1:.1f}, p{self.page})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "page": self.page,
            "width": self.x1 - self.x0,
            "height": self.y1 - self.y0,
        }


@dataclass
class LayoutElement:
    """A single element in the document layout."""

    element_type: str  # 'text', 'table', 'image', 'header', 'footer', etc.
    bbox: BoundingBox
    content: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.element_type,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "confidence": self.confidence,
            "metadata": self.metadata or {},
        }


class LayoutProcessor:
    """
    Extract document layout and structure.

    Provides:
    - Section detection (headers, paragraphs)
    - Table extraction with cell coordinates
    - Figure/image detection
    - Reading order identification
    - Spatial relationship analysis
    """

    def __init__(self):
        """Initialize layout processor."""
        self.elements: List[LayoutElement] = []

    def extract_layout(self, file_path: str) -> Dict[str, Any]:
        """
        Extract complete layout from document.

        Args:
            file_path: Path to document file

        Returns:
            Dictionary containing:
            - sections: List of text sections with headers
            - tables: List of tables with cell data
            - figures: List of images/figures
            - elements: All layout elements
            - reading_order: Elements sorted by reading order
            - metadata: Document metadata (pages, dimensions)
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        try:
            if suffix == ".pdf":
                return self._extract_pdf_layout(file_path)
            elif suffix in [".jpg", ".jpeg", ".png"]:
                return self._extract_image_layout(file_path)
            elif suffix == ".docx":
                return self._extract_docx_layout(file_path)
            else:
                raise ValueError(f"Layout extraction not supported for {suffix}")

        except Exception as e:
            logger.error(f"Layout extraction failed: {e}")
            return {
                "error": str(e),
                "sections": [],
                "tables": [],
                "figures": [],
                "elements": [],
                "reading_order": [],
                "metadata": {},
            }

    def _extract_pdf_layout(self, file_path: str) -> Dict[str, Any]:
        """Extract layout from PDF using pdfplumber or PyMuPDF."""
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed, falling back to basic extraction")
            return self._extract_pdf_basic(file_path)

        elements = []
        sections = []
        tables = []
        figures = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text with layout
                    words = page.extract_words()

                    # Group words into lines/blocks
                    lines = self._group_words_into_lines(words)

                    for line in lines:
                        bbox = BoundingBox(
                            x0=line["x0"],
                            y0=line["top"],
                            x1=line["x1"],
                            y1=line["bottom"],
                            page=page_num,
                        )

                        element = LayoutElement(
                            element_type="text",
                            bbox=bbox,
                            content=line["text"],
                            confidence=1.0,
                            metadata={
                                "font_size": line.get("font_size"),
                                "font_name": line.get("fontname"),
                            },
                        )
                        elements.append(element)

                    # Extract tables
                    page_tables = page.extract_tables()
                    for table_idx, table_data in enumerate(page_tables):
                        if table_data:
                            table_bbox = self._estimate_table_bbox(table_data, page)
                            tables.append(
                                {
                                    "data": table_data,
                                    "bbox": table_bbox.to_dict()
                                    if table_bbox
                                    else None,
                                    "page": page_num,
                                    "index": table_idx,
                                }
                            )

                            # Add table element
                            if table_bbox:
                                elements.append(
                                    LayoutElement(
                                        element_type="table",
                                        bbox=table_bbox,
                                        content=f"Table with {len(table_data)} rows",
                                        metadata={"rows": len(table_data)},
                                    )
                                )

                    # Extract images (figures)
                    images = page.images
                    for img_idx, img in enumerate(images):
                        bbox = BoundingBox(
                            x0=img.get("x0", 0),
                            y0=img.get("y0", 0),
                            x1=img.get("x1", 0),
                            y1=img.get("y1", 0),
                            page=page_num,
                        )
                        figures.append(
                            {
                                "bbox": bbox.to_dict(),
                                "page": page_num,
                                "index": img_idx,
                            }
                        )
                        elements.append(
                            LayoutElement(
                                element_type="figure",
                                bbox=bbox,
                                content="Image",
                            )
                        )

            # Detect sections based on layout
            sections = self._detect_sections(elements)

            # Compute reading order
            reading_order = self._compute_reading_order(elements)

            return {
                "sections": sections,
                "tables": tables,
                "figures": figures,
                "elements": [e.to_dict() for e in elements],
                "reading_order": [e.to_dict() for e in reading_order],
                "metadata": {
                    "total_pages": len(pdf.pages),
                    "total_elements": len(elements),
                },
            }

        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return self._extract_pdf_basic(file_path)

    def _extract_pdf_basic(self, file_path: str) -> Dict[str, Any]:
        """Basic PDF extraction without layout when pdfplumber unavailable."""
        from PyPDF2 import PdfReader

        try:
            with open(file_path, "rb") as f:
                pdf = PdfReader(f)
                elements = []

                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        elements.append(
                            LayoutElement(
                                element_type="text",
                                bbox=BoundingBox(
                                    0, 0, 612, 792, page_num
                                ),  # Standard US Letter
                                content=text,
                            )
                        )

                return {
                    "sections": [],
                    "tables": [],
                    "figures": [],
                    "elements": [e.to_dict() for e in elements],
                    "reading_order": [e.to_dict() for e in elements],
                    "metadata": {
                        "total_pages": len(pdf.pages),
                        "total_elements": len(elements),
                        "note": "Basic extraction without layout information",
                    },
                }
        except Exception as e:
            logger.error(f"Basic PDF extraction failed: {e}")
            return {
                "error": str(e),
                "sections": [],
                "tables": [],
                "figures": [],
                "elements": [],
            }

    def _extract_image_layout(self, file_path: str) -> Dict[str, Any]:
        """Extract layout from image (treat as single figure)."""
        from PIL import Image

        try:
            with Image.open(file_path) as img:
                width, height = img.size

                elements = [
                    LayoutElement(
                        element_type="figure",
                        bbox=BoundingBox(0, 0, width, height, 1),
                        content="Image",
                        metadata={
                            "width": width,
                            "height": height,
                            "format": img.format,
                        },
                    )
                ]

                return {
                    "sections": [],
                    "tables": [],
                    "figures": [
                        {
                            "bbox": elements[0].bbox.to_dict(),
                            "page": 1,
                            "index": 0,
                        }
                    ],
                    "elements": [e.to_dict() for e in elements],
                    "reading_order": [e.to_dict() for e in elements],
                    "metadata": {
                        "width": width,
                        "height": height,
                        "format": img.format,
                    },
                }
        except Exception as e:
            logger.error(f"Image layout extraction failed: {e}")
            return {"error": str(e)}

    def _extract_docx_layout(self, file_path: str) -> Dict[str, Any]:
        """Extract layout from DOCX."""
        import docx

        try:
            doc = docx.Document(file_path)
            elements = []

            for para_idx, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    elements.append(
                        LayoutElement(
                            element_type="text",
                            bbox=BoundingBox(
                                0, para_idx * 12, 612, (para_idx + 1) * 12, 1
                            ),
                            content=para.text,
                            metadata={
                                "style": para.style.name if para.style else "Normal",
                                "is_heading": para.style.name.startswith("Heading")
                                if para.style
                                else False,
                            },
                        )
                    )

            # Detect sections from headings
            sections = self._detect_sections_docx(elements)

            return {
                "sections": sections,
                "tables": [],  # DOCX table extraction can be added
                "figures": [],
                "elements": [e.to_dict() for e in elements],
                "reading_order": [e.to_dict() for e in elements],
                "metadata": {
                    "paragraph_count": len(doc.paragraphs),
                },
            }
        except Exception as e:
            logger.error(f"DOCX layout extraction failed: {e}")
            return {"error": str(e)}

    def _group_words_into_lines(self, words: List[Dict]) -> List[Dict]:
        """Group extracted words into lines based on vertical position."""
        if not words:
            return []

        # Sort by vertical position
        sorted_words = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))

        lines = []
        current_line = []
        current_top = None

        for word in sorted_words:
            word_top = round(word["top"], 1)

            if (
                current_top is None or abs(word_top - current_top) < 3
            ):  # Same line threshold
                current_line.append(word)
                current_top = word_top
            else:
                # Finish current line
                if current_line:
                    lines.append(self._merge_words_into_line(current_line))
                current_line = [word]
                current_top = word_top

        # Don't forget last line
        if current_line:
            lines.append(self._merge_words_into_line(current_line))

        return lines

    def _merge_words_into_line(self, words: List[Dict]) -> Dict:
        """Merge words in a line into a single line dict."""
        text = " ".join(w["text"] for w in words)
        x0 = min(w["x0"] for w in words)
        x1 = max(w["x1"] for w in words)
        top = min(w["top"] for w in words)
        bottom = max(w["bottom"] for w in words)

        return {
            "text": text,
            "x0": x0,
            "x1": x1,
            "top": top,
            "bottom": bottom,
        }

    def _estimate_table_bbox(self, table_data: List, page) -> Optional[BoundingBox]:
        """Estimate bounding box for a table."""
        try:
            # This is a simplified version
            # pdfplumber can provide better bbox info
            return BoundingBox(
                x0=50,  # Approximate margins
                y0=100,
                x1=page.width - 50,
                y1=page.height - 100,
                page=page.page_number,
            )
        except Exception:
            return None

    def _detect_sections(self, elements: List[LayoutElement]) -> List[Dict[str, Any]]:
        """Detect document sections from text elements."""
        sections = []
        current_section = None

        for element in elements:
            if element.element_type != "text":
                continue

            # Heuristic: short, bold, or large text = heading
            is_heading = len(element.content) < 100 and (
                element.metadata.get("font_size", 12) > 14 or element.content.isupper()
            )

            if is_heading:
                # Save previous section
                if current_section:
                    sections.append(current_section)

                # Start new section
                current_section = {
                    "heading": element.content,
                    "content": [],
                    "bbox": element.bbox.to_dict(),
                }
            else:
                if current_section is None:
                    current_section = {
                        "heading": "Introduction",
                        "content": [],
                        "bbox": element.bbox.to_dict(),
                    }
                current_section["content"].append(element.content)

        # Don't forget last section
        if current_section:
            sections.append(current_section)

        return sections

    def _detect_sections_docx(
        self, elements: List[LayoutElement]
    ) -> List[Dict[str, Any]]:
        """Detect sections from DOCX elements."""
        sections = []
        current_section = None

        for element in elements:
            if element.element_type != "text":
                continue

            is_heading = element.metadata.get("is_heading", False)

            if is_heading:
                if current_section:
                    sections.append(current_section)

                current_section = {
                    "heading": element.content,
                    "content": [],
                    "bbox": element.bbox.to_dict(),
                }
            else:
                if current_section is None:
                    current_section = {
                        "heading": "Introduction",
                        "content": [],
                        "bbox": element.bbox.to_dict(),
                    }
                current_section["content"].append(element.content)

        if current_section:
            sections.append(current_section)

        return sections

    def _compute_reading_order(
        self, elements: List[LayoutElement]
    ) -> List[LayoutElement]:
        """
        Compute reading order based on layout position.

        Standard reading order: top-to-bottom, left-to-right per page.
        """
        # Sort by page, then top-to-bottom, then left-to-right
        sorted_elements = sorted(
            elements, key=lambda e: (e.bbox.page, e.bbox.y0, e.bbox.x0)
        )
        return sorted_elements


def extract_layout(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to extract layout from a document.

    Args:
        file_path: Path to document file

    Returns:
        Layout information dictionary
    """
    processor = LayoutProcessor()
    return processor.extract_layout(file_path)


__all__ = [
    "LayoutProcessor",
    "LayoutElement",
    "BoundingBox",
    "extract_layout",
]
