import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from .models import (
    BaseAIModel, LlamaVisionModel, GPT4VisionModel, 
    GeminiModel, FallbackModel
)
import logging
import re
from typing import BinaryIO
import docx
from PyPDF2 import PdfReader
import io
from datetime import datetime
import dateutil.parser

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, rules_file: str = "config/default_rules.yaml", 
                 ai_model: Optional[str] = None):
        self.rules = self._load_rules(rules_file)
        self.supported_formats = {'.pdf', '.docx', '.txt'}

        # Initialize AI model based on preference
        self.ai_model = self._initialize_ai_model(ai_model)

    def _initialize_ai_model(self, model_name: Optional[str]) -> BaseAIModel:
        """Initialize the specified AI model with fallback options"""
        try:
            if model_name == "gpt4-vision":
                return GPT4VisionModel()
            elif model_name == "gemini":
                return GeminiModel()
            elif model_name == "llama-vision":
                return LlamaVisionModel()
            elif model_name is None:
                # Try models in order of preference
                try:
                    return GPT4VisionModel()
                except Exception as e1:
                    logger.warning(f"Failed to initialize GPT-4 Vision: {e1}")
                    try:
                        return GeminiModel()
                    except Exception as e2:
                        logger.warning(f"Failed to initialize Gemini: {e2}")
                        try:
                            return LlamaVisionModel()
                        except Exception as e3:
                            logger.warning(f"Failed to initialize Llama Vision: {e3}")
                            return FallbackModel()
            else:
                logger.warning(f"Unknown model {model_name}, using fallback")
                return FallbackModel()
        except Exception as e:
            logger.error(f"Error initializing AI model: {e}, using fallback")
            return FallbackModel()

    def _load_rules(self, rules_file: str) -> Dict:
        try:
            with open(rules_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading rules file: {e}")
            return {}

    def _parse_date(self, date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        try:
            # Parse the date string using dateutil
            parsed_date = dateutil.parser.parse(date_str)
            return parsed_date.strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return date_str

    def _parse_float(self, amount_str: str) -> float:
        """Parse string amount to float, handling different number formats"""
        try:
            # Remove any currency symbols and whitespace
            cleaned = amount_str.strip().replace('$', '').replace('€', '').replace('£', '')

            # First, remove any thousands separators (assuming US/UK format)
            if ',' in cleaned and '.' in cleaned:
                cleaned = cleaned.replace(',', '')
            # Then handle cases where comma is used as decimal separator
            elif ',' in cleaned and '.' not in cleaned:
                cleaned = cleaned.replace(',', '.')

            return float(cleaned)
        except Exception as e:
            logger.error(f"Error parsing float {amount_str}: {e}")
            return 0.0

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf = PdfReader(file)
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                # Log entire text in debug mode
                logger.debug(f"Full PDF text extracted:\n{text}")
                return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise

    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            raise

    def _extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error extracting text from TXT: {e}")
            raise

    def _extract_text(self, file_path: str) -> str:
        """Extract text from document based on file type"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        extracted_text = ""
        if suffix == '.pdf':
            extracted_text = self._extract_text_from_pdf(file_path)
        elif suffix == '.docx':
            extracted_text = self._extract_text_from_docx(file_path)
        elif suffix == '.txt':
            extracted_text = self._extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        # Log first 500 characters of extracted text for debugging
        logger.debug(f"Extracted text preview from {path.name}: {extracted_text[:500]}")
        return extracted_text

    def _convert_value(self, value: str, field_type: str) -> Any:
        """Convert extracted value to the specified type"""
        if field_type == "Date":
            return self._parse_date(value)
        elif field_type == "Float":
            return self._parse_float(value)
        elif field_type == "Int":
            return int(float(self._parse_float(value)))
        else:  # String or unknown type
            return value

    def _extract_metadata(self, text: str, doc_type: str) -> Dict:
        """Extract metadata using patterns from rules"""
        metadata = {}
        fields = self.rules.get('rules', {}).get(doc_type, {}).get('metadata_fields', {})

        logger.debug(f"Attempting to extract metadata for type '{doc_type}'")
        logger.debug(f"Available fields: {fields}")

        required_fields = []
        for field_name, field_config in fields.items():
            if field_config.get('required', False):
                required_fields.append(field_name)

            pattern = field_config.get('pattern', '')
            if field_name == 'total_amount':
                # Updated pattern to better handle currency amounts with thousands separators
                pattern = r'(?i)(?:total|amount|sum|betrag|summe|rechnungsbetrag)[\s:]*[$€£]?\s*([\d,]+\.?\d{0,2})'

            logger.debug(f"Using pattern for {field_name}: {pattern}")

            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            if matches:
                # Extract the first captured group or the entire match
                value = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
                # Convert value to the specified type
                field_type = field_config.get('type', 'String')
                converted_value = self._convert_value(value, field_type)
                metadata[field_name] = converted_value
                logger.debug(f"Field {field_name}: found and converted to {field_type}")
            elif field_name in required_fields:
                logger.warning(f"Required field {field_name} not found in document")

        return metadata

    def _classify_document(self, text: str) -> str:
        """Classify document based on content and rules"""
        max_matches = 0
        doc_type = "unknown"

        # Log classification attempt
        logger.debug("Starting document classification")

        for type_name, type_rules in self.rules.get('rules', {}).items():
            keywords = type_rules.get('keywords', [])
            matches = sum(1 for keyword in keywords if keyword.lower() in text.lower())
            logger.debug(f"Document type '{type_name}' matched {matches} keywords")
            if matches > max_matches:
                max_matches = matches
                doc_type = type_name

        logger.debug(f"Final classification: {doc_type}")
        return doc_type

    def process_document(self, file_path: str, use_ocr: bool = False) -> Dict:
        try:
            path = Path(file_path)
            if path.suffix.lower() not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {path.suffix}")

            # Extract text based on file type
            text = self._extract_text(file_path)

            # Use AI model for enhanced extraction if available
            ai_analysis = None
            try:
                ai_analysis = self.ai_model.extract_information(
                    text=text,
                    image_path=file_path if path.suffix.lower() == '.pdf' else None
                )
            except Exception as e:
                logger.warning(f"AI model analysis failed: {e}")

            # Traditional processing
            doc_type = self._classify_document(text)
            metadata = self._extract_metadata(text, doc_type)

            result = {
                "file_name": path.name,
                "document_type": doc_type,
                "metadata": metadata,
                "text_length": len(text),
                "ai_analysis": ai_analysis
            }

            logger.info(f"Successfully processed document: {path.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            raise