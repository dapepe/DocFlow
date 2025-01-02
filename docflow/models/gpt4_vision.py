"""
GPT-4 Vision Model Implementation
Provides document analysis using OpenAI's GPT-4 Vision model
"""
import os
import base64
from typing import Dict, Any, Optional
from openai import OpenAI
from . import BaseModel, ModelRegistry
import logging
import json

logger = logging.getLogger(__name__)

class GPT4VisionModel(BaseModel):
    """GPT-4 Vision model for document analysis"""
    description = "GPT-4 Vision model for advanced document analysis"
    requires_env_vars = ['OPENAI_API_KEY']

    # Document analysis schema
    ANALYSIS_SCHEMA = {
        "document_type": "Type of document (invoice, contract, report, etc.)",
        "content_summary": "Brief summary of the document content",
        "key_information": {
            "dates": ["List of important dates found"],
            "amounts": ["List of monetary amounts"],
            "reference_numbers": ["Document reference numbers, invoice numbers, etc."],
        },
        "entities": {
            "organizations": ["Company names"],
            "people": ["Person names"],
            "locations": ["Location names"]
        },
        "metadata": {
            "total_amount": "Total amount if present",
            "due_date": "Payment due date if present",
            "document_date": "Document creation/issue date"
        }
    }

    def __init__(self):
        """Initialize the model with configuration from environment"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('GPT4_VISION_MODEL', 'gpt-4-vision-preview')  # Updated default model
        self.client = OpenAI(api_key=self.api_key)
        self.max_tokens = int(os.getenv('GPT4_MAX_TOKENS', '1000'))
        self.temperature = float(os.getenv('GPT4_TEMPERATURE', '0.2'))
        self.prompt_template = os.getenv('GPT4_PROMPT_TEMPLATE', 
            """Analyze this document and extract key information according to this schema:
            {schema}

            Provide ONLY a JSON response following the schema exactly, no additional text.
            Focus on accuracy and completeness of the extracted information.""")

    @classmethod
    def is_available(cls) -> bool:
        """Check if OpenAI API key is configured"""
        api_key = os.getenv('OPENAI_API_KEY')
        logger.debug(f"Checking GPT-4 Vision availability: API key {'present' if api_key else 'missing'}")
        return bool(api_key)

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using GPT-4 Vision model"""
        try:
            messages = []

            # Prepare system message with schema
            messages.append({
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": self.prompt_template.format(
                            schema=json.dumps(self.ANALYSIS_SCHEMA, indent=2)
                        )
                    }
                ]
            })

            # Prepare user message with content
            user_content = []

            # Add text content if available
            if text:
                user_content.append({
                    "type": "text",
                    "text": f"Document text content:\n{text}"
                })

            # Add image if available
            if image_path:
                try:
                    with open(image_path, "rb") as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        })
                except Exception as e:
                    logger.error(f"Error processing image {image_path}: {e}")
                    # Continue with text-only analysis if image processing fails
                    pass

            messages.append({
                "role": "user",
                "content": user_content
            })

            # Make request to OpenAI API
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    response_format={"type": "json_object"}
                )

                analysis = json.loads(response.choices[0].message.content)

                return {
                    "raw_analysis": analysis,
                    "model_name": self.model,
                    "success": True
                }

            except Exception as e:
                logger.error(f"OpenAI API request failed: {e}")
                raise Exception(f"Failed to communicate with OpenAI API: {str(e)}")

        except Exception as e:
            logger.error(f"Error in GPT-4 Vision analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model
            }

# Register the GPT-4 Vision model
ModelRegistry.register("gpt4-vision", GPT4VisionModel)