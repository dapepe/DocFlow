import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import logging
from pathlib import Path
import base64
import os
import pdf2image  # For converting PDF pages to images
from PIL import Image
import io

logger = logging.getLogger(__name__)

class BaseAIModel(ABC):
    """Base class for AI model integrations"""

    @abstractmethod
    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information from text and optionally an image"""
        pass

class LlamaVisionModel(BaseAIModel):
    """Integration with Ollama via HTTP API"""

    def __init__(self, model_name: str = "gpt4-mini"):
        self.model_name = model_name
        self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._check_availability()

    def _check_availability(self):
        """Check if Ollama service is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise ConnectionError("Ollama service not available")
            available_models = response.json().get("models", [])
            if self.model_name not in [m.get("name") for m in available_models]:
                logger.warning(f"Model {self.model_name} not found in available models")
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
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
        """Extract information using GPT4-mini through Ollama API"""
        try:
            # Prepare the prompt
            prompt = f"""Analyze this document and extract key information.

            Text content:
            {text}

            Please extract:
            1. Document type
            2. Key dates
            3. Important numbers/amounts
            4. Names and entities
            5. Key points or summary
            """

            # Prepare the API request
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9
                }
            }

            # If image is provided, add it to the payload
            if image_path and Path(image_path).exists():
                payload["images"] = [self._encode_image(image_path)]

            # Make API request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.text}")

            result = response.json()

            return {
                "raw_analysis": result.get("response", ""),
                "model_name": self.model_name,
                "success": True
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Ollama service: {e}")
            return {
                "success": False,
                "error": "Ollama service unavailable",
                "model_name": self.model_name
            }
        except Exception as e:
            logger.error(f"Error in GPT4-mini extraction: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model_name
            }

class GPT4VisionModel(BaseAIModel):
    """Integration with OpenAI's GPT-4 Vision API"""

    def __init__(self, model_name: str = "gpt-4"):
        self.model_name = model_name
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            logger.warning("OpenAI package not available. GPT-4 Vision features will be disabled.")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            raise

    def _convert_pdf_to_image(self, pdf_path: str) -> bytes:
        """Convert first page of PDF to PNG image"""
        try:
            # Convert first page of PDF to PIL Image
            images = pdf2image.convert_from_path(pdf_path, first_page=1, last_page=1)
            if not images:
                raise ValueError("Failed to convert PDF to image")

            # Convert PIL Image to PNG bytes
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr.getvalue()
        except Exception as e:
            logger.error(f"Error converting PDF to image: {e}")
            raise

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64, converting PDF if necessary"""
        try:
            if Path(image_path).suffix.lower() == '.pdf':
                image_bytes = self._convert_pdf_to_image(image_path)
                return base64.b64encode(image_bytes).decode('utf-8')
            else:
                with open(image_path, 'rb') as img_file:
                    return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            raise

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using GPT-4 Vision"""
        try:
            if not hasattr(self, 'client'):
                raise ValueError("OpenAI client not initialized")

            # Construct the message content
            content = [{
                "type": "text",
                "text": f"""Analyze this document and extract key information.

Text content:
{text}

Please extract:
1. Document type
2. Key dates
3. Important numbers/amounts
4. Names and entities
5. Key points or summary"""
            }]

            # Add image if provided
            if image_path and Path(image_path).exists():
                base64_image = self._encode_image(image_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": content
                }],
                max_tokens=1000
            )

            return {
                "raw_analysis": response.choices[0].message.content,
                "model_name": self.model_name,
                "success": True
            }

        except ImportError:
            logger.warning("OpenAI package not available, skipping GPT-4 Vision analysis")
            return {
                "success": False,
                "error": "OpenAI package not available",
                "model_name": self.model_name
            }
        except Exception as e:
            logger.error(f"Error in GPT-4 Vision extraction: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model_name
            }

class GeminiModel(BaseAIModel):
    """Integration with Google's Gemini Vision API"""

    def __init__(self, model_name: str = "gemini-pro-vision"):
        self.model_name = model_name
        self._init_client()

    def _init_client(self):
        """Initialize Gemini client"""
        try:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            genai.configure(api_key=api_key)
            self.genai = genai
        except ImportError:
            logger.warning("Google Generative AI package not available. Gemini features will be disabled.")
        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")
            raise

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using Gemini Vision"""
        try:
            if not hasattr(self, 'genai'):
                raise ValueError("Gemini client not initialized")

            prompt = f"""Analyze this document and extract key information.

            Text content:
            {text}

            Please extract:
            1. Document type
            2. Key dates
            3. Important numbers/amounts
            4. Names and entities
            5. Key points or summary"""

            # Initialize model
            model = self.genai.GenerativeModel(self.model_name)

            # Prepare content parts
            content_parts = [prompt]

            # Add image if provided
            if image_path and Path(image_path).exists():
                image = self.genai.types.Image.load_from_file(image_path)
                content_parts.append(image)

            # Generate response
            response = model.generate_content(content_parts)

            return {
                "raw_analysis": response.text,
                "model_name": self.model_name,
                "success": True
            }

        except ImportError:
            logger.warning("Google Generative AI package not available, skipping Gemini analysis")
            return {
                "success": False,
                "error": "Google Generative AI package not available",
                "model_name": self.model_name
            }
        except Exception as e:
            logger.error(f"Error in Gemini extraction: {e}")
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