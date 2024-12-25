import docling
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging.config

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, rules_file: str = "config/rules.yaml"):
        self.rules = self._load_rules(rules_file)
        
    def _load_rules(self, rules_file: str) -> dict:
        try:
            with open(rules_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load rules: {str(e)}")
            return {"document_rules": []}

    def process_document(self, file_path: Union[str, Path], 
                        use_ocr: bool = False) -> Dict:
        """Process a document and extract metadata."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Initialize document processing
            doc = docling.Document(str(file_path))
            
            # Extract text (with optional OCR)
            if use_ocr and file_path.suffix.lower() == '.pdf':
                text = doc.extract_text(ocr=True)
            else:
                text = doc.extract_text()

            # Classify document
            doc_type = self._classify_document(text)
            
            # Extract metadata
            metadata = self._extract_metadata(text, doc_type)
            
            # Extract numerical data
            numbers = doc.extract_numbers()

            return {
                "document_type": doc_type,
                "metadata": metadata,
                "numerical_data": numbers,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _classify_document(self, text: str) -> str:
        """Classify document based on keyword rules."""
        text = text.lower()
        
        for rule in self.rules.get('document_rules', []):
            keywords = rule.get('keywords', [])
            if any(keyword.lower() in text for keyword in keywords):
                return rule['name']
        
        return "unknown"

    def _extract_metadata(self, text: str, doc_type: str) -> Dict:
        """Extract metadata based on document type."""
        metadata = {}
        
        # Get metadata fields for document type
        fields = next(
            (rule['metadata_fields'] 
             for rule in self.rules.get('document_rules', [])
             if rule['name'] == doc_type),
            []
        )

        # Use docling to extract metadata for each field
        for field in fields:
            try:
                value = docling.extract_field(text, field)
                if value:
                    metadata[field] = value
            except:
                continue

        return metadata
