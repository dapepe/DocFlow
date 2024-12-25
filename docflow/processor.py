import yaml
from pathlib import Path
from typing import Dict, List, Optional
import logging
import re
from typing import BinaryIO, Union
import docx
from PyPDF2 import PdfReader
import io

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, rules_file: str = "config/default_rules.yaml"):
        self.rules = self._load_rules(rules_file)
        self.supported_formats = {'.pdf', '.docx', '.txt'}

    def _load_rules(self, rules_file: str) -> Dict:
        try:
            with open(rules_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading rules file: {e}")
            return {}

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf = PdfReader(file)
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
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

    def _extract_metadata(self, text: str, doc_type: str) -> Dict:
        metadata = {}
        patterns = self.rules.get('extraction_patterns', {})
        fields = self.rules.get('rules', {}).get(doc_type, {}).get('metadata_fields', [])

        for field in fields:
            if field in patterns:
                matches = re.findall(patterns[field], text)
                if matches:
                    # For total_amount, only take the full amount, not the decimal part
                    if field == 'total_amount':
                        metadata[field] = matches[0][0]  # Get the full amount
                    else:
                        metadata[field] = matches[0]

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

            # Classify document
            doc_type = self._classify_document(text)

            # Extract metadata
            metadata = self._extract_metadata(text, doc_type)

            result = {
                "file_name": path.name,
                "document_type": doc_type,
                "metadata": metadata,
                "text_length": len(text)
            }

            logger.info(f"Successfully processed document: {path.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            raise