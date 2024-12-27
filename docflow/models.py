from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, BinaryIO
import logging
from pathlib import Path
import base64

logger = logging.getLogger(__name__)

class BaseAIModel(ABC):
    """Base class for AI model integrations"""

    @abstractmethod
    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information from text and optionally an image"""
        pass

class LlamaVisionModel(BaseAIModel):
    """Integration with Llama 3.2 Vision via Ollama"""

    def __init__(self, model_name: str = "llama2-vision"):
        self.model_name = model_name
        self._ensure_model()

    def _ensure_model(self):
        """Ensure the model is available in Ollama"""
        try:
            # Try importing ollama only when needed
            import ollama
            # Check if model exists, pull if it doesn't
            ollama.pull(self.model_name)
        except ImportError:
            logger.warning("Ollama Python package not available. LlamaVision features will be disabled.")
        except Exception as e:
            logger.error(f"Error ensuring model availability: {e}")
            raise

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        try:
            with open(image_path, 'rb') as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            raise

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using Llama Vision"""
        try:
            # Try importing ollama only when needed
            import ollama

            # Prepare the prompt
            prompt = f"""Analyze the following document and extract key information.
            If an image is provided, describe any relevant visual elements.

            Text content:
            {text}

            Please extract:
            1. Document type
            2. Key dates
            3. Important numbers/amounts
            4. Names and entities
            5. Key points or summary
            """

            # Prepare the message
            message = {"role": "user", "content": prompt}

            # If image is provided, add it to the message
            if image_path:
                if not Path(image_path).exists():
                    raise FileNotFoundError(f"Image not found: {image_path}")

                encoded_image = self._encode_image(image_path)
                message["images"] = [encoded_image]

            # Get response from model
            response = ollama.chat(
                model=self.model_name,
                messages=[message],
                stream=False
            )

            # Process and structure the response
            raw_response = response['message']['content']

            return {
                "raw_analysis": raw_response,
                "model_name": self.model_name,
                "success": True
            }

        except ImportError:
            logger.warning("Ollama package not available, skipping AI analysis")
            return {
                "success": False,
                "error": "Ollama package not available",
                "model_name": self.model_name
            }
        except Exception as e:
            logger.error(f"Error in Llama Vision extraction: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model_name
            }

class FallbackModel(BaseAIModel):
    """Fallback model when no AI service is available"""

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Provide basic text analysis without AI"""
        try:
            # Basic text analysis
            words = text.split()
            word_count = len(words)

            # Simple metrics
            analysis = {
                "text_length": len(text),
                "word_count": word_count,
                "has_image": image_path is not None
            }

            return {
                "raw_analysis": analysis,
                "model_name": "fallback",
                "success": True
            }
        except Exception as e:
            logger.error(f"Error in fallback analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": "fallback"
            }