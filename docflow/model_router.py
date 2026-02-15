"""
Intelligent Model Routing

Automatically selects the best model based on document characteristics:
- Content type (Invoice, Receipt, Contract, etc.)
- Complexity (Text-heavy, Image-heavy, Tables)
- Language (English, Multi-lingual)
- Requirements (Speed vs Accuracy)
"""

import structlog
from typing import Dict, Any, Optional, List
from .models import ModelRegistry

logger = structlog.get_logger(__name__)


class ModelRouter:
    """Routes documents to the optimal AI model."""

    # Default routing rules
    # Map document characteristics to preferred models
    # Ordered by preference
    RULES = {
        "invoice": ["claude-vision", "gpt4-vision", "qwen-vision"],
        "receipt": ["qwen2.5-vl", "gemini-vision", "llama-vision"],
        "financial_report": ["claude-vision", "gpt4-vision"],
        "handwritten": ["olmocr-7b", "gemini-vision", "gpt4-vision"],
        "technical_drawing": ["claude-vision", "gpt4-vision"],
        "fast_processing": ["gemini-vision", "llama3.2-vision", "gemma"],
        "offline": ["qwen2.5-vl", "llama3.2-vision", "llava"],
        "complex_layout": ["docling-local", "claude-vision"],
    }

    def __init__(self):
        self.available_models = ModelRegistry.list_models()

    def route(
        self,
        document_type: str = "unknown",
        has_images: bool = False,
        is_handwritten: bool = False,
        requires_ocr: bool = False,
        priority: str = "balanced",  # speed, accuracy, balanced
    ) -> str:
        """
        Select the best model for the given document context.

        Args:
            document_type: Detected document type (invoice, receipt, etc.)
            has_images: Whether the document contains images
            is_handwritten: Whether the document contains handwriting
            requires_ocr: Whether the document needs OCR
            priority: Optimization priority ('speed', 'accuracy', 'balanced')

        Returns:
            Model ID string
        """
        candidates = []

        # 1. Specialized Routing
        if is_handwritten:
            candidates.extend(self.RULES.get("handwritten", []))

        if document_type in self.RULES:
            candidates.extend(self.RULES[document_type])

        # 2. Capability-based Routing
        if priority == "speed":
            candidates.extend(self.RULES.get("fast_processing", []))

        if requires_ocr or has_images:
            # Prefer vision models
            candidates.extend(["qwen2.5-vl", "gemini-vision", "llama3.2-vision"])

        # 3. Fallback to robust general models
        candidates.extend(["claude-vision", "gpt4-vision", "qwen-vision"])

        # 4. Selection
        selected_model = self._select_best_available(candidates)

        logger.info(
            "model_routing_decision",
            selected_model=selected_model,
            document_type=document_type,
            priority=priority,
            candidates=candidates[:3],
        )

        return selected_model

    def _select_best_available(self, candidates: List[str]) -> str:
        """Select the first available model from candidates."""
        # Refresh availability list occasionally? For now assume static since init
        # actually, better to check live availability or trust the list from init
        # Re-fetching list_models might be expensive if it checks connections.
        # Let's trust ModelRegistry.list_models() is somewhat cached or fast.

        # In a real system, we'd cache this list and update it periodically.
        # For now, we assume the keys in self.available_models are valid.

        for model_id in candidates:
            if model_id in self.available_models:
                return model_id

        # Ultimate fallback
        return "fallback"


# Global instance
model_router = ModelRouter()
