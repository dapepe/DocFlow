from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, BinaryIO
import logging
from pathlib import Path
import base64
import os

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
            try:
                ollama.pull(self.model_name)
                logger.info(f"Successfully pulled {self.model_name} model")
            except Exception as e:
                logger.warning(f"Failed to pull model {self.model_name}: {e}")
                raise
        except ImportError:
            logger.warning("Ollama Python package not available. LlamaVision features will be disabled.")
            raise
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

            # Prepare the message
            message = {"role": "user", "content": prompt}

            # If image is provided, add it to the message
            if image_path and Path(image_path).exists():
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

class GPT4VisionModel(BaseAIModel):
    """Integration with OpenAI's GPT-4 Vision API"""

    def __init__(self, model_name: str = "gpt-4-vision-preview-1106"):
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

    def _encode_image_for_openai(self, image_path: str) -> str:
        """Convert image to base64 for OpenAI API"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image for OpenAI: {e}")
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
                base64_image = self._encode_image_for_openai(image_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
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