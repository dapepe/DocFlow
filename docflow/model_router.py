"""
Intelligent Model Router

Automatically selects the optimal model based on document characteristics.
Routes to specialized models for specific document types, languages, and requirements.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from ..models import ModelRegistry

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Routes documents to the best available model.

    Routing logic considers:
    - Document type (invoice, contract, receipt, etc.)
    - Language (multilingual vs English-only)
    - Content type (text-heavy vs image-heavy)
    - Speed requirements (fast vs accurate)
    - Model availability and capabilities

    Usage:
        router = ModelRouter()
        model_name = router.select_model({
            'document_type': 'invoice',
            'has_images': True,
            'language': 'de',
            'priority': 'accuracy'
        })
    """

    def __init__(self):
        """Initialize the model router."""
        self.routing_rules = self._load_routing_rules()

    def _load_routing_rules(self) -> Dict[str, Any]:
        """Load routing rules for different document scenarios."""
        return {
            # Document type mappings
            "document_types": {
                "invoice": {
                    "preferred": ["claude-vision", "qwen2.5-vl", "gemini-vision"],
                    "fallback": ["qwen-vision", "gpt4-vision", "fallback"],
                    "reason": "Invoices need high accuracy for amounts, dates, and vendor info",
                },
                "receipt": {
                    "preferred": ["olmocr-7b", "qwen2.5-vl", "gemini-vision"],
                    "fallback": ["llava", "qwen-vision", "fallback"],
                    "reason": "Receipts often need OCR-focused processing",
                },
                "contract": {
                    "preferred": ["claude-vision", "llama3.2-vision", "granite-vision"],
                    "fallback": ["qwen-vision", "gemma", "fallback"],
                    "reason": "Contracts need reasoning and legal language understanding",
                },
                "handwritten": {
                    "preferred": ["olmocr-7b", "qwen2.5-vl"],
                    "fallback": ["mistral-document", "qwen-vision", "fallback"],
                    "reason": "Handwritten documents need specialized OCR",
                },
                "multilingual": {
                    "preferred": ["qwen2.5-vl", "gemini-vision", "claude-vision"],
                    "fallback": ["qwen-vision", "llava", "fallback"],
                    "reason": "Non-English documents need multilingual models",
                },
                "fast": {
                    "preferred": ["gemini-vision", "gemma", "llama3.2-vision"],
                    "fallback": ["qwen-vision", "llava", "fallback"],
                    "reason": "Fast processing prioritizes speed over ultimate accuracy",
                },
            },
            # Language mappings
            "languages": {
                "en": ["claude-vision", "gemini-vision", "gpt4-vision"],
                "de": ["qwen2.5-vl", "gemini-vision", "claude-vision"],
                "fr": ["qwen2.5-vl", "gemini-vision", "claude-vision"],
                "es": ["qwen2.5-vl", "gemini-vision", "claude-vision"],
                "zh": ["qwen2.5-vl", "qwen-vision", "gemini-vision"],
                "ja": ["qwen2.5-vl", "gemini-vision", "claude-vision"],
                "ko": ["qwen2.5-vl", "gemini-vision", "claude-vision"],
                "ar": ["qwen2.5-vl", "gemini-vision"],
                "ru": ["qwen2.5-vl", "gemini-vision", "claude-vision"],
            },
            # Content type mappings
            "content_types": {
                "text_heavy": ["claude-vision", "granite-vision", "gemma"],
                "image_heavy": ["qwen2.5-vl", "llama3.2-vision", "gemini-vision"],
                "mixed": ["claude-vision", "qwen2.5-vl", "gemini-vision"],
                "ocr_critical": ["olmocr-7b", "qwen2.5-vl", "mistral-document"],
            },
            # Capability requirements
            "capabilities": {
                "requires_gpu": ["llama3.2-vision", "qwen2.5-vl"],
                "streaming_capable": ["gemini-vision", "openrouter-claude"],
                "json_native": ["gemini-vision"],
            },
        }

    def select_model(
        self,
        document_type: Optional[str] = None,
        has_images: bool = False,
        language: str = "en",
        priority: str = "balanced",  # 'speed', 'accuracy', 'balanced'
        requires_ocr: bool = False,
        available_models: Optional[List[str]] = None,
    ) -> str:
        """
        Select the best model for a given document.

        Args:
            document_type: Type of document (invoice, contract, etc.)
            has_images: Whether document contains images
            language: Document language code (en, de, etc.)
            priority: 'speed', 'accuracy', or 'balanced'
            requires_ocr: Whether OCR is critical
            available_models: List of available model names (auto-detected if None)

        Returns:
            Selected model name
        """
        if available_models is None:
            available_models = list(ModelRegistry.list_models().keys())

        logger.info(
            f"Selecting model for: type={document_type}, lang={language}, "
            f"images={has_images}, priority={priority}"
        )

        candidates = []

        # 1. Check document type specific models
        if document_type and document_type in self.routing_rules["document_types"]:
            rules = self.routing_rules["document_types"][document_type]
            preferred = rules["preferred"]
            logger.debug(f"Document type '{document_type}' prefers: {preferred}")

            for model in preferred:
                if model in available_models:
                    candidates.append(
                        {"model": model, "score": 100, "reason": rules["reason"]}
                    )
                    break

        # 2. Check language-specific models
        if language in self.routing_rules["languages"]:
            lang_models = self.routing_rules["languages"][language]
            logger.debug(f"Language '{language}' prefers: {lang_models}")

            for i, model in enumerate(lang_models):
                if model in available_models:
                    score = 90 - (i * 5)
                    existing = next(
                        (c for c in candidates if c["model"] == model), None
                    )
                    if existing:
                        existing["score"] = max(existing["score"], score)
                    else:
                        candidates.append(
                            {
                                "model": model,
                                "score": score,
                                "reason": f"Optimized for {language} language",
                            }
                        )

        # 3. Check content type
        if requires_ocr:
            ocr_models = self.routing_rules["content_types"]["ocr_critical"]
            for i, model in enumerate(ocr_models):
                if model in available_models:
                    score = 85 - (i * 5)
                    existing = next(
                        (c for c in candidates if c["model"] == model), None
                    )
                    if existing:
                        existing["score"] = max(existing["score"], score)
                    else:
                        candidates.append(
                            {
                                "model": model,
                                "score": score,
                                "reason": "Specialized OCR capabilities",
                            }
                        )

        elif has_images:
            image_models = self.routing_rules["content_types"]["image_heavy"]
            for i, model in enumerate(image_models):
                if model in available_models:
                    score = 80 - (i * 5)
                    existing = next(
                        (c for c in candidates if c["model"] == model), None
                    )
                    if existing:
                        existing["score"] = max(existing["score"], score)
                    else:
                        candidates.append(
                            {
                                "model": model,
                                "score": score,
                                "reason": "Strong vision capabilities",
                            }
                        )

        # 4. Apply priority adjustments
        if priority == "speed":
            fast_models = self.routing_rules["document_types"]["fast"]["preferred"]
            for c in candidates:
                if c["model"] in fast_models:
                    c["score"] += 10
                    c["reason"] += " (fast)"

        elif priority == "accuracy":
            # Boost premium models
            premium = ["claude-vision", "gemini-vision", "qwen2.5-vl"]
            for c in candidates:
                if c["model"] in premium:
                    c["score"] += 15
                    c["reason"] += " (high accuracy)"

        # 5. Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 6. Select best available
        if candidates:
            selected = candidates[0]["model"]
            logger.info(
                f"Selected model: {selected} (score: {candidates[0]['score']}, "
                f"reason: {candidates[0]['reason']})"
            )
            return selected

        # 7. Fallback to primary model or first available
        if "qwen-vision" in available_models:
            logger.info("No specific match found, using default: qwen-vision")
            return "qwen-vision"
        elif available_models:
            selected = available_models[0]
            logger.info(f"No specific match found, using first available: {selected}")
            return selected

        # 8. Ultimate fallback
        logger.warning("No models available, returning fallback")
        return "fallback"

    def get_model_recommendation(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a document file and recommend the best model.

        Args:
            file_path: Path to document file

        Returns:
            Dictionary with recommendation details
        """
        path = Path(file_path)

        # Detect document characteristics
        characteristics = self._analyze_document(file_path)

        # Select model
        model = self.select_model(
            document_type=characteristics.get("document_type"),
            has_images=characteristics.get("has_images", False),
            language=characteristics.get("language", "en"),
            requires_ocr=characteristics.get("requires_ocr", False),
        )

        return {
            "recommended_model": model,
            "characteristics": characteristics,
            "confidence": "high" if characteristics.get("document_type") else "medium",
        }

    def _analyze_document(self, file_path: str) -> Dict[str, Any]:
        """Analyze document to detect characteristics."""
        path = Path(file_path)
        characteristics = {
            "file_name": path.name,
            "extension": path.suffix.lower(),
        }

        # Detect if image file
        if path.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            characteristics["has_images"] = True
            characteristics["requires_ocr"] = True

        # Detect if PDF (might contain images)
        elif path.suffix.lower() == ".pdf":
            characteristics["has_images"] = True  # Assume might have images

        # Try to detect document type from filename
        filename_lower = path.name.lower()
        if any(word in filename_lower for word in ["invoice", "rechnung", "facture"]):
            characteristics["document_type"] = "invoice"
        elif any(word in filename_lower for word in ["receipt", "quittung", "ticket"]):
            characteristics["document_type"] = "receipt"
        elif any(
            word in filename_lower for word in ["contract", "vertrag", "agreement"]
        ):
            characteristics["document_type"] = "contract"
        elif any(word in filename_lower for word in ["handwritten", "handschrift"]):
            characteristics["document_type"] = "handwritten"
            characteristics["requires_ocr"] = True

        return characteristics

    def list_routing_rules(self) -> Dict[str, Any]:
        """Return all routing rules for documentation."""
        return self.routing_rules


def get_optimal_model(
    file_path: Optional[str] = None,
    document_type: Optional[str] = None,
    language: str = "en",
    priority: str = "balanced",
) -> str:
    """
    Convenience function to get optimal model.

    Args:
        file_path: Path to document (for auto-detection)
        document_type: Explicit document type
        language: Document language
        priority: 'speed', 'accuracy', or 'balanced'

    Returns:
        Recommended model name
    """
    router = ModelRouter()

    if file_path:
        rec = router.get_model_recommendation(file_path)
        return rec["recommended_model"]
    else:
        return router.select_model(
            document_type=document_type, language=language, priority=priority
        )


__all__ = ["ModelRouter", "get_optimal_model"]
