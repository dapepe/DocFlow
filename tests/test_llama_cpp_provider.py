"""
Test suite for llama.cpp provider and GGUF models.

Tests cover:
- Provider initialization and configuration
- Model availability detection
- Error handling for missing models
- Integration with ModelRegistry
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Skip all tests if llama-cpp-python not installed
try:
    from docflow.models.providers import LlamaCppProvider
    from docflow.models import ModelRegistry

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not LLAMA_CPP_AVAILABLE, reason="llama-cpp-python not installed"
)


class TestLlamaCppProvider:
    """Test LlamaCppProvider base functionality."""

    def test_provider_initialization(self):
        """Test provider initializes with correct defaults."""
        with patch.object(
            LlamaCppProvider, "_get_model_path", return_value="/fake/model.gguf"
        ):
            provider = LlamaCppProvider()

            assert provider.config["n_ctx"] == 8192
            assert provider.config["n_gpu_layers"] == 0
            assert provider.config["temperature"] == 0.2
            assert provider.llm is None  # Lazy loading

    def test_provider_configuration_from_env(self):
        """Test provider reads configuration from environment."""
        env_vars = {
            "LLAMA_CPP_N_CTX": "16384",
            "LLAMA_CPP_N_GPU_LAYERS": "20",
            "LLAMA_CPP_TEMPERATURE": "0.5",
            "LLAMA_CPP_MAX_TOKENS": "4096",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch.object(
                LlamaCppProvider, "_get_model_path", return_value="/fake/model.gguf"
            ):
                provider = LlamaCppProvider()

                assert provider.config["n_ctx"] == 16384
                assert provider.config["n_gpu_layers"] == 20
                assert provider.config["temperature"] == 0.5
                assert provider.config["max_tokens"] == 4096

    def test_model_availability_missing_file(self):
        """Test is_available returns False when model file doesn't exist."""
        with patch.object(
            LlamaCppProvider, "_get_model_path", return_value="/nonexistent/model.gguf"
        ):
            assert not LlamaCppProvider.is_available()

    def test_model_availability_existing_file(self):
        """Test is_available returns True when model file exists."""
        with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch.object(
                LlamaCppProvider, "_get_model_path", return_value=tmp_path
            ):
                assert LlamaCppProvider.is_available()
        finally:
            os.unlink(tmp_path)

    def test_get_capabilities(self):
        """Test capability reporting."""
        with patch.object(
            LlamaCppProvider, "_get_model_path", return_value="/fake/model.gguf"
        ):
            provider = LlamaCppProvider()
            caps = provider.get_capabilities()

            assert caps["vision"] is True
            assert caps["multilingual"] is True
            assert caps["local"] is True
            assert caps["structured_output"] is True

    def test_schema_loading(self):
        """Test JSON schema is loaded correctly."""
        mock_schema = {"type": "object", "properties": {}}

        with patch.object(
            LlamaCppProvider, "_get_model_path", return_value="/fake/model.gguf"
        ):
            with patch(
                "builtins.open",
                mock_open(read_data='{"type": "object", "properties": {}}'),
            ):
                with patch("os.getenv", return_value="config/schema.json"):
                    provider = LlamaCppProvider()
                    assert provider.schema is not None


class TestQwen25VLModel:
    """Test Qwen2.5-VL model implementation."""

    def test_model_registration(self):
        """Test model is registered in ModelRegistry."""
        from docflow.models.qwen25_vl import Qwen25VLModel

        model_class = ModelRegistry.get_model("qwen2.5-vl")
        assert model_class is not None
        assert model_class == Qwen25VLModel

    def test_model_description(self):
        """Test model has correct description."""
        from docflow.models.qwen25_vl import Qwen25VLModel

        assert "Qwen2.5-VL" in Qwen25VLModel.description
        assert "multilingual" in Qwen25VLModel.description.lower()

    def test_model_path_from_env(self):
        """Test model path is read from environment."""
        from docflow.models.qwen25_vl import Qwen25VLModel

        with patch.dict(os.environ, {"LLAMA_CPP_QWEN25_VL_PATH": "/custom/path.gguf"}):
            path = Qwen25VLModel._get_model_path()
            assert path == "/custom/path.gguf"

    def test_capabilities(self):
        """Test Qwen2.5-VL capabilities."""
        from docflow.models.qwen25_vl import Qwen25VLModel

        with patch.object(
            Qwen25VLModel, "_get_model_path", return_value="/fake/model.gguf"
        ):
            model = Qwen25VLModel()
            caps = model.get_capabilities()

            assert caps["multilingual"] is True
            assert caps["vision"] is True
            assert caps["ocr"] is True


class TestLlama32VisionModel:
    """Test Llama 3.2 Vision model implementation."""

    def test_model_registration(self):
        """Test model is registered in ModelRegistry."""
        from docflow.models.llama32_vision import Llama32VisionModel

        model_class = ModelRegistry.get_model("llama3.2-vision")
        assert model_class is not None
        assert model_class == Llama32VisionModel

    def test_chat_format_configuration(self):
        """Test model uses llama-3 chat format."""
        from docflow.models.llama32_vision import Llama32VisionModel

        with patch.object(
            Llama32VisionModel, "_get_model_path", return_value="/fake/model.gguf"
        ):
            model = Llama32VisionModel()
            assert model.config["chat_format"] == "llama-3"


class TestOlmOCRModel:
    """Test olmOCR model implementation."""

    def test_model_registration(self):
        """Test model is registered in ModelRegistry."""
        from docflow.models.olmocr_model import OlmOCRModel

        model_class = ModelRegistry.get_model("olmocr-7b")
        assert model_class is not None
        assert model_class == OlmOCRModel

    def test_ocr_specialization(self):
        """Test olmOCR is marked as specialized OCR."""
        from docflow.models.olmocr_model import OlmOCRModel

        with patch.object(
            OlmOCRModel, "_get_model_path", return_value="/fake/model.gguf"
        ):
            model = OlmOCRModel()
            caps = model.get_capabilities()

            assert caps["specialized_ocr"] is True
            assert caps["ocr"] is True


class TestProviderErrorHandling:
    """Test error handling in provider."""

    def test_missing_model_file_error(self):
        """Test proper error when model file missing."""
        with patch.object(
            LlamaCppProvider, "_get_model_path", return_value="/nonexistent/model.gguf"
        ):
            provider = LlamaCppProvider()

            with pytest.raises((FileNotFoundError, RuntimeError)):
                provider._load_model()

    def test_missing_llama_cpp_import(self):
        """Test error when llama-cpp-python not installed."""
        with patch.dict("sys.modules", {"llama_cpp": None}):
            with patch.object(
                LlamaCppProvider, "_get_model_path", return_value="/fake/model.gguf"
            ):
                provider = LlamaCppProvider()

                with pytest.raises((ImportError, RuntimeError)):
                    provider._load_model()


class TestModelRegistryIntegration:
    """Test integration with ModelRegistry."""

    def test_all_gguf_models_registered(self):
        """Test all GGUF models are in registry."""
        expected_models = ["qwen2.5-vl", "llama3.2-vision", "olmocr-7b"]

        for model_name in expected_models:
            model_class = ModelRegistry.get_model(model_name)
            assert model_class is not None, f"Model {model_name} not registered"

    def test_model_descriptions_available(self):
        """Test all models have descriptions."""
        models = ModelRegistry.list_models()

        for model_name, description in models.items():
            assert description is not None
            assert len(description) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
