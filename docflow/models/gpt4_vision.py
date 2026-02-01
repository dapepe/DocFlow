"""
GPT-4 Vision Model Implementation
Provides document analysis using GPT-4 Vision model via OpenAI API
"""
from typing import Dict, Any, Optional, List
import os
import base64
import json
from openai import OpenAI
import logging
from ..models import BaseModel
from . import ModelRegistry
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)

class GPT4VisionModel(BaseModel):
    """GPT-4 Vision model for document analysis"""
    description = "GPT-4 Vision model for advanced document analysis"
    requires_env_vars = ['OPENAI_API_KEY']

    def __init__(self):
        """Initialize the model with configuration from environment"""
        super().__init__()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('GPT4_VISION_MODEL', 'gpt-4-turbo')
        self.client = OpenAI(api_key=self.api_key)
        self.max_tokens = int(os.getenv('GPT4_MAX_TOKENS', '1000'))
        self.temperature = float(os.getenv('GPT4_TEMPERATURE', '0.2'))
        self.schema = self._load_schema()

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
        model_instructions = prompt_manager.get_model_specific_instructions('gpt4-vision')
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

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information from text and/or image using GPT-4 Vision"""
        try:
            messages = [{"role": "system", "content": "You are a document analysis expert."}]
            
            # Prepare the content parts
            content_parts: List[Dict] = [{"type": "text", "text": self._get_enhanced_prompt(text)}]
            
            # Add image if available
            if image_path:
                base64_image = self._encode_image(image_path)
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                })
            
            messages.append({"role": "user", "content": content_parts})

            # Make the API request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            # Parse the response
            if response.choices and response.choices[0].message.content:
                try:
                    result = json.loads(response.choices[0].message.content)
                    return {
                        "raw_analysis": result,
                        "model_name": self.model,
                        "success": True
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse GPT-4 Vision response: {e}")
                    return {
                        "success": False,
                        "error": "Invalid JSON response",
                        "model_name": self.model
                    }
            else:
                logger.error("Empty response from GPT-4 Vision")
                return {
                    "success": False,
                    "error": "Empty response",
                    "model_name": self.model
                }

        except Exception as e:
            logger.error(f"Error in GPT-4 Vision analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model
            }

    @classmethod
    def is_available(cls) -> bool:
        """Check if the model is available"""
        api_key_present = bool(os.getenv('OPENAI_API_KEY'))
        logger.debug(f"Checking GPT-4 Vision availability: API key present")
        return api_key_present

# Register the GPT-4 Vision model
ModelRegistry.register("gpt4-vision", GPT4VisionModel)