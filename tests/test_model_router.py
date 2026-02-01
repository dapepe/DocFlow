"""
Test suite for ModelRouter.

Tests cover:
- Model selection based on document characteristics
- Routing rules validation
- Fallback behavior
- Document analysis
"""

import pytest
from unittest.mock import patch, MagicMock
from docflow.model_router import ModelRouter, get_optimal_model


class TestModelRouter:
    """Test ModelRouter functionality."""

    @pytest.fixture
    def router(self):
        """Create a ModelRouter instance."""
        return ModelRouter()

    @pytest.fixture
    def mock_available_models(self):
        """Mock available models for testing."""
        return [
            "qwen2.5-vl",
            "llama3.2-vision",
            "olmocr-7b",
            "claude-vision",
            "gemini-vision",
            "qwen-vision",
            "gpt4-vision",
            "fallback",
        ]

    def test_router_initialization(self, router):
        """Test router initializes with routing rules."""
        assert router.routing_rules is not None
        assert "document_types" in router.routing_rules
        assert "languages" in router.routing_rules

    def test_select_model_for_invoice(self, router, mock_available_models):
        """Test model selection for invoices."""
        model = router.select_model(
            document_type="invoice", available_models=mock_available_models
        )

        # Should prefer high-accuracy models for invoices
        assert model in ["claude-vision", "qwen2.5-vl", "gemini-vision", "qwen-vision"]

    def test_select_model_for_receipt(self, router, mock_available_models):
        """Test model selection for receipts."""
        model = router.select_model(
            document_type="receipt", available_models=mock_available_models
        )

        # Should prefer OCR-capable models
        assert model in [
            "olmocr-7b",
            "qwen2.5-vl",
            "gemini-vision",
            "llava",
            "qwen-vision",
        ]

    def test_select_model_for_handwritten(self, router, mock_available_models):
        """Test model selection for handwritten documents."""
        model = router.select_model(
            document_type="handwritten", available_models=mock_available_models
        )

        # Should prefer specialized OCR
        assert model in ["olmocr-7b", "qwen2.5-vl", "mistral-document", "qwen-vision"]

    def test_select_model_by_language_german(self, router, mock_available_models):
        """Test model selection for German documents."""
        model = router.select_model(
            language="de", available_models=mock_available_models
        )

        # Should prefer multilingual models
        assert model in ["qwen2.5-vl", "gemini-vision", "claude-vision", "qwen-vision"]

    def test_select_model_by_language_chinese(self, router, mock_available_models):
        """Test model selection for Chinese documents."""
        model = router.select_model(
            language="zh", available_models=mock_available_models
        )

        # Should prefer Qwen for Chinese
        assert model in ["qwen2.5-vl", "qwen-vision", "gemini-vision"]

    def test_select_model_with_images(self, router, mock_available_models):
        """Test model selection for image-heavy documents."""
        model = router.select_model(
            has_images=True, available_models=mock_available_models
        )

        # Should prefer vision models
        assert model in [
            "qwen2.5-vl",
            "llama3.2-vision",
            "gemini-vision",
            "claude-vision",
            "qwen-vision",
        ]

    def test_select_model_ocr_critical(self, router, mock_available_models):
        """Test model selection when OCR is critical."""
        model = router.select_model(
            requires_ocr=True, available_models=mock_available_models
        )

        # Should prefer OCR-specialized models
        assert model in ["olmocr-7b", "qwen2.5-vl", "mistral-document"]

    def test_select_model_priority_speed(self, router, mock_available_models):
        """Test model selection with speed priority."""
        model = router.select_model(
            priority="speed", available_models=mock_available_models
        )

        # Should prefer fast models
        assert model in ["gemini-vision", "gemma", "llama3.2-vision", "qwen-vision"]

    def test_select_model_priority_accuracy(self, router, mock_available_models):
        """Test model selection with accuracy priority."""
        model = router.select_model(
            document_type="contract",
            priority="accuracy",
            available_models=mock_available_models,
        )

        # Should prefer premium models
        assert model in ["claude-vision", "gemini-vision", "qwen2.5-vl"]

    def test_fallback_to_default(self, router):
        """Test fallback when no specific match."""
        model = router.select_model(available_models=["qwen-vision", "fallback"])

        assert model == "qwen-vision"

    def test_fallback_to_first_available(self, router):
        """Test fallback to first available when no default."""
        model = router.select_model(available_models=["llava", "fallback"])

        assert model == "llava"

    def test_ultimate_fallback(self, router):
        """Test ultimate fallback when nothing available."""
        model = router.select_model(available_models=[])

        assert model == "fallback"

    def test_analyze_document_from_filename_invoice(self, router):
        """Test document analysis from invoice filename."""
        characteristics = router._analyze_document("/path/to/invoice_2024.pdf")

        assert characteristics["document_type"] == "invoice"
        assert characteristics["extension"] == ".pdf"

    def test_analyze_document_from_filename_receipt(self, router):
        """Test document analysis from receipt filename."""
        characteristics = router._analyze_document("/path/to/receipt_store.pdf")

        assert characteristics["document_type"] == "receipt"

    def test_analyze_document_from_filename_contract(self, router):
        """Test document analysis from contract filename."""
        characteristics = router._analyze_document("/path/to/contract_agreement.pdf")

        assert characteristics["document_type"] == "contract"

    def test_analyze_document_image_file(self, router):
        """Test document analysis for image files."""
        characteristics = router._analyze_document("/path/to/document.jpg")

        assert characteristics["has_images"] is True
        assert characteristics["requires_ocr"] is True
        assert characteristics["extension"] == ".jpg"

    def test_analyze_document_pdf(self, router):
        """Test document analysis for PDF files."""
        characteristics = router._analyze_document("/path/to/document.pdf")

        assert characteristics["has_images"] is True  # PDFs might have images
        assert characteristics["extension"] == ".pdf"

    def test_get_model_recommendation(self, router, mock_available_models):
        """Test full model recommendation flow."""
        with patch.object(ModelRouter, "_analyze_document") as mock_analyze:
            mock_analyze.return_value = {
                "document_type": "invoice",
                "language": "de",
                "has_images": True,
            }

            with patch.object(ModelRouter, "select_model", return_value="qwen2.5-vl"):
                recommendation = router.get_model_recommendation("/path/to/doc.pdf")

                assert recommendation["recommended_model"] == "qwen2.5-vl"
                assert "characteristics" in recommendation
                assert "confidence" in recommendation


class TestGetOptimalModel:
    """Test get_optimal_model convenience function."""

    def test_get_optimal_model_with_file_path(self):
        """Test get_optimal_model with file path."""
        with patch("docflow.model_router.ModelRouter") as MockRouter:
            mock_instance = MagicMock()
            mock_instance.get_model_recommendation.return_value = {
                "recommended_model": "claude-vision"
            }
            MockRouter.return_value = mock_instance

            model = get_optimal_model(file_path="/path/to/invoice.pdf")

            assert model == "claude-vision"

    def test_get_optimal_model_with_explicit_params(self):
        """Test get_optimal_model with explicit parameters."""
        with patch("docflow.model_router.ModelRouter") as MockRouter:
            mock_instance = MagicMock()
            mock_instance.select_model.return_value = "qwen2.5-vl"
            MockRouter.return_value = mock_instance

            model = get_optimal_model(
                document_type="invoice", language="de", priority="accuracy"
            )

            assert model == "qwen2.5-vl"


class TestRoutingRules:
    """Test routing rules structure."""

    def test_document_type_rules_exist(self):
        """Test that document type rules are defined."""
        router = ModelRouter()

        expected_types = [
            "invoice",
            "receipt",
            "contract",
            "handwritten",
            "multilingual",
            "fast",
        ]

        for doc_type in expected_types:
            assert doc_type in router.routing_rules["document_types"]
            assert "preferred" in router.routing_rules["document_types"][doc_type]
            assert "fallback" in router.routing_rules["document_types"][doc_type]

    def test_language_rules_exist(self):
        """Test that language rules are defined."""
        router = ModelRouter()

        expected_languages = ["en", "de", "fr", "es", "zh", "ja", "ko", "ar", "ru"]

        for lang in expected_languages:
            assert lang in router.routing_rules["languages"]
            assert len(router.routing_rules["languages"][lang]) > 0

    def test_content_type_rules_exist(self):
        """Test that content type rules are defined."""
        router = ModelRouter()

        expected_types = ["text_heavy", "image_heavy", "mixed", "ocr_critical"]

        for content_type in expected_types:
            assert content_type in router.routing_rules["content_types"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
