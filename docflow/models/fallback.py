"""
Fallback Model Implementation
Provides basic text analysis without AI dependencies
"""
import re
import os
from typing import Dict, Any, Optional
from . import BaseModel, ModelRegistry
import logging

logger = logging.getLogger(__name__)

class FallbackModel(BaseModel):
    """Fallback model for basic text analysis when AI services are unavailable"""
    description = "Basic text analysis without AI dependencies"

    def __init__(self):
        """Initialize fallback model with optional environment configuration"""
        # Allow customization of confidence threshold via environment
        self.confidence_threshold = float(os.getenv('FALLBACK_CONFIDENCE_THRESHOLD', '0.6'))

        # Load custom patterns from environment if available
        self.date_pattern = os.getenv('FALLBACK_DATE_PATTERN', 
                                    r'\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}')
        self.amount_pattern = os.getenv('FALLBACK_AMOUNT_PATTERN',
                                      r'(?:[\$€£]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:EUR|USD|GBP))')

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
            dates = re.findall(self.date_pattern, text)

            # Look for monetary amounts
            amounts = re.findall(self.amount_pattern, text)

            # Basic document type detection
            doc_type = "unknown"
            type_patterns = {
                'invoice': r'invoice|rechnung|facture',
                'receipt': r'receipt|quittung|reçu',
                'contract': r'contract|vertrag|contrat',
                'report': r'report|bericht|rapport'
            }

            # Load additional patterns from environment
            env_patterns = os.getenv('FALLBACK_DOCTYPE_PATTERNS')
            if env_patterns:
                try:
                    import json
                    custom_patterns = json.loads(env_patterns)
                    type_patterns.update(custom_patterns)
                except Exception as e:
                    logger.warning(f"Failed to load custom document type patterns: {e}")

            # Detect document type
            for doc_type_name, pattern in type_patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    doc_type = doc_type_name
                    break

            analysis = {
                "document_type": doc_type,
                "text_length": len(text),
                "word_count": word_count,
                "dates_found": dates,
                "amounts_found": amounts,
                "has_image": image_path is not None,
                "confidence": self.confidence_threshold
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