"""
Fallback Model Implementation
Provides basic text analysis without AI dependencies
"""
import re
from typing import Dict, Any, Optional
from . import BaseModel, ModelRegistry
import logging

logger = logging.getLogger(__name__)

class FallbackModel(BaseModel):
    """Fallback model for basic text analysis when AI services are unavailable"""
    description = "Basic text analysis without AI dependencies"
    
    @classmethod
    def is_available(cls) -> bool:
        """Fallback model is always available"""
        return True
    
    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Provide basic text analysis using regex patterns"""
        try:
            # Basic text analysis
            words = text.split()
            word_count = len(words)
            
            # Look for potential dates
            date_pattern = r'\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}'
            dates = re.findall(date_pattern, text)
            
            # Look for monetary amounts
            amount_pattern = r'(?:[\$€£]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:EUR|USD|GBP))'
            amounts = re.findall(amount_pattern, text)
            
            # Basic document type detection
            doc_type = "unknown"
            if re.search(r'invoice|rechnung|facture', text, re.IGNORECASE):
                doc_type = "invoice"
            elif re.search(r'receipt|quittung|reçu', text, re.IGNORECASE):
                doc_type = "receipt"
            
            analysis = {
                "document_type": doc_type,
                "text_length": len(text),
                "word_count": word_count,
                "dates_found": dates,
                "amounts_found": amounts,
                "has_image": image_path is not None,
                "confidence": 0.6  # Fixed confidence for fallback model
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

# Register the fallback model
ModelRegistry.register("fallback", FallbackModel)
