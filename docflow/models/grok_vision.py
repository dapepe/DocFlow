"""
Grok Vision Model Implementation
Provides document analysis using xAI's Grok Vision API
"""
import os
from typing import Dict, Any, Optional
from openai import OpenAI
import base64
from . import BaseModel, ModelRegistry
import logging

logger = logging.getLogger(__name__)

class GrokVisionModel(BaseModel):
    """Grok Vision model using xAI's API for document analysis"""
    description = "Grok Vision model for advanced document analysis"
    requires_env_vars = ['XAI_API_KEY']
    
    def __init__(self):
        """Initialize the model with configuration from environment"""
        self.api_key = os.getenv('XAI_API_KEY')
        self.model = os.getenv('GROK_MODEL', 'grok-2-vision-1212')
        self.client = OpenAI(base_url="https://api.x.ai/v1", api_key=self.api_key)
        self.prompt_template = os.getenv('GROK_PROMPT_TEMPLATE', 
            """Analyze this document and extract key information:
            1. Document type/category
            2. Important dates
            3. Monetary amounts
            4. Key entities (people, companies)
            5. Important details specific to the document type
            
            Provide the analysis in a structured JSON format.
            """)
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if xAI API key is configured"""
        return bool(os.getenv('XAI_API_KEY'))
    
    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using Grok Vision model"""
        try:
            messages = []
            
            # Add system prompt
            messages.append({
                "role": "system",
                "content": "You are a document analysis expert. Analyze the provided document and extract key information in a structured format."
            })
            
            # Add image if available
            if image_path:
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self.prompt_template
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    })
            else:
                # Text-only analysis
                messages.append({
                    "role": "user",
                    "content": f"{self.prompt_template}\n\nText to analyze:\n{text}"
                })
            
            # Make request to xAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "raw_analysis": analysis,
                "model_name": self.model,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in Grok Vision analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model
            }

# Register the Grok Vision model
ModelRegistry.register("grok-vision", GrokVisionModel)
