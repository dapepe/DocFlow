"""AI model integrations for document processing"""
import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import logging
from pathlib import Path
import base64
import os
import pdf2image
from PIL import Image
import io

logger = logging.getLogger(__name__)

class ModelNotAvailableError(Exception):
    """Raised when a model is not available due to missing dependencies or API keys"""
    pass

class BaseAIModel(ABC):
    """Base class for AI model integrations"""

    @abstractmethod
    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information from text and optionally an image"""
        pass

    @classmethod
    def validate_environment(cls) -> bool:
        """Validate that all required environment variables are present"""
        return True

class LlamaVisionModel(BaseAIModel):
    """Integration with Ollama via HTTP API"""

    def __init__(self):
        self.model_name = "llama-3.2-vision"
        self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._check_availability()

    def _check_availability(self):
        """Check if Ollama service is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise ModelNotAvailableError("Ollama service not available")
            logger.debug(f"Available Ollama models: {response.json()}")
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
            raise ModelNotAvailableError(f"Ollama service error: {e}")

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            prompt = f"""Analyze this document and extract key information.

            Text content:
            {text}

            Please extract and format the response as JSON with these fields:
            1. document_type: The type of document (e.g., invoice, contract, report)
            2. dates: List of important dates found
            3. amounts: List of monetary amounts found
            4. entities: List of names and organizations
            5. key_fields: Map of key fields like invoice numbers, reference numbers, etc.
            """

            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            }

            if image_path and Path(image_path).exists():
                with open(image_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    payload["images"] = [img_data]

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.text}")

            return {
                "raw_analysis": response.json().get("response", ""),
                "model_name": self.model_name,
                "success": True
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

    def __init__(self):
        self.model_name = "gpt-4-vision"  
        self._init_client()

    @classmethod
    def validate_environment(cls) -> bool:
        """Check if OpenAI API key is available"""
        return bool(os.getenv("OPENAI_API_KEY"))

    def _init_client(self):
        """Initialize OpenAI client"""
        try:
            if not self.validate_environment():
                raise ModelNotAvailableError("OPENAI_API_KEY environment variable not set")

            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info("OpenAI client initialized successfully")
        except ImportError:
            raise ModelNotAvailableError("OpenAI package not installed")
        except Exception as e:
            raise ModelNotAvailableError(f"Error initializing OpenAI client: {e}")

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            messages = [
                {
                    "role": "system",
                    "content": ("You are a document analysis expert. Extract key information from "
                              "documents and format the output as JSON.")
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analyze this document and extract the following information as JSON:
                            - document_type: The type of document
                            - dates: Any important dates
                            - amounts: Any monetary amounts
                            - invoice_number: Invoice number if present
                            - entities: Names of people or organizations

                            Text content:
                            {text}"""
                        }
                    ]
                }
            ]

            if image_path and Path(image_path).exists():
                with open(image_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    messages[-1]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_data}"
                        }
                    })

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return {
                "raw_analysis": result,
                "model_name": self.model_name,
                "success": True
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

    def __init__(self):
        self.model_name = "gemini-pro-vision"
        self._init_client()

    @classmethod
    def validate_environment(cls) -> bool:
        """Check if Google API key is available"""
        return bool(os.getenv("GOOGLE_API_KEY"))

    def _init_client(self):
        """Initialize Gemini client"""
        try:
            if not self.validate_environment():
                raise ModelNotAvailableError("GOOGLE_API_KEY environment variable not set")

            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.genai = genai
            logger.info("Gemini client initialized successfully")
        except ImportError:
            raise ModelNotAvailableError("Google Generative AI package not installed")
        except Exception as e:
            raise ModelNotAvailableError(f"Error initializing Gemini client: {e}")

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            prompt = f"""Analyze this document and extract the following information as JSON:
            - document_type: The type of document
            - dates: Any important dates
            - amounts: Any monetary amounts
            - invoice_number: Invoice number if present
            - entities: Names of people or organizations

            Text content:
            {text}"""

            # Initialize model
            model = self.genai.GenerativeModel(self.model_name)

            # Prepare content parts
            content_parts = [prompt]

            # Add image if provided
            if image_path and Path(image_path).exists():
                image = self.genai.types.Image.load_from_file(image_path)
                content_parts.append(image)

            # Generate response
            response = model.generate_content(
                content_parts,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.9,
                }
            )

            # Try to parse response as JSON
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                result = {"text": response.text}

            return {
                "raw_analysis": result,
                "model_name": self.model_name,
                "success": True
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

            # Look for potential dates (simple regex)
            import re
            date_pattern = r'\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}'
            dates = re.findall(date_pattern, text)

            # Look for monetary amounts
            amount_pattern = r'(?:[\$€£]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:EUR|USD|GBP))'
            amounts = re.findall(amount_pattern, text)

            analysis = {
                "text_length": len(text),
                "word_count": word_count,
                "dates_found": dates,
                "amounts_found": amounts,
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

def get_available_models() -> Dict[str, str]:
    """Return a dictionary of available models and their descriptions"""
    models = {
        "llama-vision": "Llama 3.2 Vision via Ollama (default)",
        "gpt4-vision": "OpenAI's GPT-4 Vision API",
        "gemini": "Google's Gemini Pro Vision",
        "fallback": "Basic text analysis without AI"
    }

    # Check which models are actually available
    available = {}
    for model_id, description in models.items():
        try:
            if model_id == "llama-vision":
                LlamaVisionModel()._check_availability()
                available[model_id] = description
            elif model_id == "gpt4-vision" and GPT4VisionModel.validate_environment():
                available[model_id] = description
            elif model_id == "gemini" and GeminiModel.validate_environment():
                available[model_id] = description
            elif model_id == "fallback":
                available[model_id] = description
        except Exception as e:
            logger.debug(f"Model {model_id} not available: {e}")
            continue

    return available