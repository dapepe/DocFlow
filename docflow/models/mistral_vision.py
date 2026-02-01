"""
Mistral Document AI Model Implementation
Provides document analysis and OCR using Mistral API
"""
from typing import Dict, Any, Optional, List
import os
import base64
import json
import requests
import logging
from ..models import BaseModel
from . import ModelRegistry
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)

class MistralDocumentModel(BaseModel):
    """Mistral Document AI model for document analysis and OCR"""
    description = "Mistral Document AI with OCR capabilities"
    requires_env_vars = ['MISTRAL_API_KEY']

    def __init__(self):
        """Initialize the model with configuration from environment"""
        super().__init__()
        self.api_key = os.getenv('MISTRAL_API_KEY')
        self.model = os.getenv('MISTRAL_MODEL', 'pixtral-12b-2409')
        self.api_base_url = os.getenv('MISTRAL_API_BASE_URL', 'https://api.mistral.ai/v1')
        self.max_tokens = int(os.getenv('MISTRAL_MAX_TOKENS', '1000'))
        self.temperature = float(os.getenv('MISTRAL_TEMPERATURE', '0.2'))
        self.schema = self._load_schema()
        
        # Setup headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _load_schema(self) -> dict:
        """Load JSON schema from file"""
        schema_path = os.getenv('DOCFLOW_SCHEMA_PATH', 'config/schema.json')
        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema from {schema_path}: {e}")
            raise

    def _get_enhanced_prompt(self, text: str, document_type: str = None, file_extension: str = None) -> str:
        """Get enhanced prompt using the configurable prompt system"""
        model_instructions = prompt_manager.get_model_specific_instructions('mistral-document')
        return prompt_manager.generate_prompt(
            document_text=text,
            schema=self.schema,
            document_type=document_type,
            file_extension=file_extension,
            model_specific_instructions=model_instructions
        )

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _get_image_mime_type(self, image_path: str) -> str:
        """Get MIME type from image file extension"""
        extension = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(extension, 'image/jpeg')

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information from text and/or image using Mistral Document AI"""
        try:
            # Prepare the messages
            messages = [
                {
                    "role": "system", 
                    "content": "You are a document analysis expert with OCR capabilities. Extract information accurately from documents."
                }
            ]
            
            # Prepare content parts
            content_parts = [{"type": "text", "text": self._get_enhanced_prompt(text)}]
            
            # Add image if available
            if image_path:
                base64_image = self._encode_image(image_path)
                mime_type = self._get_image_mime_type(image_path)
                content_parts.append({
                    "type": "image_url",
                    "image_url": f"data:{mime_type};base64,{base64_image}"
                })
            
            messages.append({"role": "user", "content": content_parts})

            # Prepare the API request payload
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"}
            }

            # Make the API request
            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                response_data = response.json()
                
                if 'choices' in response_data and response_data['choices']:
                    content = response_data['choices'][0]['message']['content']
                    try:
                        result = json.loads(content)
                        return {
                            "raw_analysis": result,
                            "model_name": self.model,
                            "success": True
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Mistral response: {e}")
                        return {
                            "success": False,
                            "error": "Invalid JSON response",
                            "model_name": self.model
                        }
                else:
                    logger.error("Empty response from Mistral API")
                    return {
                        "success": False,
                        "error": "Empty response",
                        "model_name": self.model
                    }
            else:
                error_msg = f"Mistral API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "model_name": self.model
                }

        except Exception as e:
            logger.error(f"Error in Mistral Document AI analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model
            }

    @classmethod
    def is_available(cls) -> bool:
        """Check if the model is available"""
        api_key_present = bool(os.getenv('MISTRAL_API_KEY'))
        logger.debug(f"Checking Mistral Document AI availability: API key present = {api_key_present}")
        return api_key_present

# Register the Mistral Document AI model
ModelRegistry.register("mistral-document", MistralDocumentModel)