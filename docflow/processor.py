import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from .models import (
    BaseAIModel, LlamaVisionModel, GPT4VisionModel, 
    GeminiModel, FallbackModel, ModelNotAvailableError,
    get_available_models
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
    def __init__(self, rules_file: str = "config/rules.yaml", 
                 ai_model: Optional[str] = None):
        self.rules = self._load_rules(rules_file)
        self.supported_formats = {'.pdf', '.docx', '.txt'}

        # Get available models
        self.available_models = get_available_models()
        logger.info(f"Available AI models: {list(self.available_models.keys())}")

        # Initialize AI model based on preference
        self.ai_model = self._initialize_ai_model(ai_model)

    def _initialize_ai_model(self, model_name: Optional[str]) -> BaseAIModel:
        """Initialize the specified AI model with fallback options"""
        logger.debug(f"Initializing AI model: {model_name}")

        try:
            if model_name not in self.available_models and model_name is not None:
                logger.warning(f"Requested model '{model_name}' not available")
                model_name = None

            if model_name == "llama-vision" or (model_name is None and "llama-vision" in self.available_models):
                return LlamaVisionModel()
            elif model_name == "gpt4-vision" and "gpt4-vision" in self.available_models:
                return GPT4VisionModel()
            elif model_name == "gemini" and "gemini" in self.available_models:
                return GeminiModel()
            elif model_name == "fallback" or model_name is None:
                return FallbackModel()

        except ModelNotAvailableError as e:
            logger.warning(f"Model '{model_name}' not available: {e}")
        except Exception as e:
            logger.error(f"Error initializing model '{model_name}': {e}")

        # Default to fallback model
        logger.info("Using fallback model for document analysis")
        return FallbackModel()

    def get_supported_models(self) -> Dict[str, str]:
        """Return dictionary of available models and their descriptions"""
        return self.available_models

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
            # Clean up the date string
            date_str = date_str.strip()
            # Parse the date string using dateutil
            parsed_date = dateutil.parser.parse(date_str)
            # Validate year is reasonable (between 1900 and 2100)
            if parsed_date.year < 1900 or parsed_date.year > 2100:
                raise ValueError(f"Invalid year in date: {parsed_date.year}")
            return parsed_date.strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            raise ValueError(f"Invalid date format: {date_str}")

    def _parse_float(self, amount_str: str) -> float:
        """Parse string amount to float, handling different number formats"""
        try:
            # Remove any currency symbols and whitespace
            cleaned = amount_str.strip().replace('$', '').replace('€', '').replace('£', '')

            # Handle European number format (1.234,56)
            if '.' in cleaned and ',' in cleaned:
                # Remove thousands separator (dot) and replace decimal comma with dot
                cleaned = cleaned.replace('.', '').replace(',', '.')
            # Handle cases where comma is used as decimal separator
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

        for field_name, field_config in fields.items():
            pattern = field_config.get('pattern', '')
            if field_name == 'total_amount':
                pattern = r'(?i)(?:total\s+net|amount\s+due|total|amount|sum|betrag|summe|rechnungsbetrag)[\s:]*[$€£]?\s*([\d.,]+(?:[\.,]\d{2})?)\s*[$€£]?'
            elif field_name == 'date':
                pattern = r'(?i)(?:invoice\s+date|date|datum|belegdatum)[\s:]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})'
            elif field_name == 'invoice_number':
                # Updated pattern to handle various invoice number formats including GC-2024/12/01
                pattern = r'(?i)Invoice\s+No\.?:\s*((?:[A-Za-z]{1,4}[-]?\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:[A-Za-z0-9][-A-Za-z0-9/]*[A-Za-z0-9]))'

            logger.debug(f"Using pattern for {field_name}: {pattern}")

            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            if matches:
                value = matches[0]
                if isinstance(value, tuple):
                    value = value[0]
                try:
                    field_type = field_config.get('type', 'String')
                    converted_value = self._convert_value(value, field_type)
                    if field_type == 'Date' and converted_value == value:
                        logger.warning(f"Failed to parse date value: {value}")
                        continue
                    metadata[field_name] = converted_value
                    logger.debug(f"Field {field_name}: found and converted to {field_type}")
                except Exception as e:
                    logger.error(f"Error converting field {field_name}: {e}")
                    continue

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
                "text_content": text,
                "ai_analysis": ai_analysis
            }

            logger.info(f"Successfully processed document: {path.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            raise