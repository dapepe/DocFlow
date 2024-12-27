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
    """Integration with Ollama via HTTP API for LLaVA/Llama models"""

    def __init__(self, model_variant="llava"):
        # Allow selecting between llava and llama-3.2-vision
        self.model_variant = model_variant
        self.model_name = "llava" if model_variant == "llava" else "llama-3.2-vision"
        self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        try:
            self._check_availability()
        except Exception as e:
            logger.warning(f"Ollama initialization failed: {e}")
            raise ModelNotAvailableError(
                "Ollama service not available. Please ensure Ollama is installed and running. "
                "Visit https://ollama.ai for installation instructions."
            )

    def _check_availability(self):
        """Check if Ollama service and selected model is available"""
        try:
            # Add timeout to prevent hanging
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ModelNotAvailableError(
                    f"Ollama service returned status code: {response.status_code}"
                )

            # Check if selected model is available
            models = response.json().get('models', [])
            model_exists = any(m.get('name', '').startswith(self.model_name) for m in models)
            if not model_exists:
                raise ModelNotAvailableError(
                    f"{self.model_name} model not found in Ollama. "
                    f"Run 'ollama pull {self.model_name}' to download it."
                )

            logger.info(f"Successfully connected to Ollama service. Model {self.model_name} is available.")
            logger.debug(f"Available Ollama models: {response.json()}")
        except requests.exceptions.ConnectionError as e:
            raise ModelNotAvailableError(
                "Cannot connect to Ollama service. Please ensure Ollama is installed and running "
                "on http://localhost:11434 or set OLLAMA_HOST environment variable."
            )
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
            raise ModelNotAvailableError(f"Ollama service error: {e}")

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            prompt = f"""Analyze this document and extract key information.

            Text content:
            {text}

            Please analyze this document and extract the following information in JSON format:
            {{
                "document_type": "The type of document (e.g., invoice, contract, report)",
                "dates": ["List of all dates found in the document"],
                "amounts": ["List of all monetary amounts"],
                "invoice_number": "If this is an invoice, extract the invoice number",
                "entities": {{
                    "organizations": ["List of company names"],
                    "people": ["List of person names"]
                }},
                "summary": "A brief summary of the document's purpose"
            }}

            For invoices, pay special attention to:
            - Invoice numbers (usually prefixed with 'Invoice No:', 'Invoice #', etc.)
            - Total amounts (look for 'Total:', 'Amount due:', etc.)
            - Company details (both supplier and recipient)
            """

            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "stop": ["}"]  # Stop after JSON completion
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

            # Try to parse response as JSON
            try:
                text_response = response.json().get("response", "")
                # Find the JSON object in the response
                json_start = text_response.find("{")
                json_end = text_response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = text_response[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = {"text": text_response}
            except json.JSONDecodeError:
                result = {"text": text_response}

            return {
                "raw_analysis": result,
                "model_name": self.model_name,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error in LLaVA extraction: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model_name
            }

class GPT4VisionModel(BaseAIModel):
    """Integration with OpenAI's GPT-4 Vision API"""

    def __init__(self):
        self.model_name = "gpt-4-turbo"  
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
        "llava": "LLaVA via Ollama (requires Ollama installation: https://ollama.ai)",
        "llama-vision": "Llama 3.2 Vision via Ollama (requires Ollama installation)",
        "gpt4-vision": "OpenAI's GPT-4 Vision API (requires OPENAI_API_KEY)",
        "gemini": "Google's Gemini Pro Vision (requires GOOGLE_API_KEY)",
        "fallback": "Basic text analysis without AI"
    }

    # Check which models are actually available
    available = {}
    for model_id, description in models.items():
        try:
            if model_id in ["llava", "llama-vision"]:
                available[model_id] = description
            elif model_id == "gpt4-vision" and GPT4VisionModel.validate_environment():
                available[model_id] = description
            elif model_id == "gemini" and GeminiModel.validate_environment():
                available[model_id] = description
            elif model_id == "fallback":
                available[model_id] = description
        except Exception as e:
            logger.debug(f"Model {model_id} not available: {e}")
            if model_id in ["llava", "llama-vision"]:
                available[model_id] = description  # Still show Ollama models even if service is not running
            continue

    return available