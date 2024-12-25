import docling
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import logging
import re

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

    def _extract_metadata(self, text: str, doc_type: str) -> Dict:
        metadata = {}
        patterns = self.rules.get('extraction_patterns', {})
        fields = self.rules.get('rules', {}).get(doc_type, {}).get('metadata_fields', [])

        for field in fields:
            if field in patterns:
                matches = re.findall(patterns[field], text)
                if matches:
                    metadata[field] = matches[0]
            
        return metadata

    def _classify_document(self, text: str) -> str:
        max_matches = 0
        doc_type = "unknown"

        for type_name, type_rules in self.rules.get('rules', {}).items():
            keywords = type_rules.get('keywords', [])
            matches = sum(1 for keyword in keywords if keyword.lower() in text.lower())
            if matches > max_matches:
                max_matches = matches
                doc_type = type_name

        return doc_type

    def process_document(self, file_path: str, use_ocr: bool = False) -> Dict:
        try:
            path = Path(file_path)
            if path.suffix.lower() not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {path.suffix}")

            # Use docling to extract text
            doc = docling.Document(file_path)
            text = doc.extract_text(use_ocr=use_ocr)

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
