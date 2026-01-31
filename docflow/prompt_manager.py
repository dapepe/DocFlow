"""
Prompt Management System
Handles configurable prompts with placeholder substitution
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages prompts with configurable templates and placeholder substitution"""

    def __init__(self, prompt_file: str = "config/prompt.txt"):
        self.prompt_file = prompt_file
        self.template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load the master prompt template from file"""
        try:
            prompt_path = Path(self.prompt_file)
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    template = f.read()
                logger.info(f"Loaded prompt template from {self.prompt_file}")
                return template
            else:
                logger.warning(
                    f"Prompt file {self.prompt_file} not found, using default template"
                )
                return self._get_default_template()
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            return self._get_default_template()

    def _get_default_template(self) -> str:
        """Fallback default template"""
        return """Analyze this document and extract the key information according to the provided schema.

Document to analyze:
{document_text}

Required Schema:
{schema_json}

Requirements:
1. Use YYYY-MM-DD for all dates
2. Use numbers for amounts (not strings)  
3. Provide ONLY the JSON response, no additional text"""

    def _generate_context_hints(
        self, document_type: Optional[str] = None, file_extension: Optional[str] = None
    ) -> str:
        """Generate context-specific hints based on document characteristics"""
        hints = []

        if document_type:
            type_hints = {
                "invoice": [
                    "Look for invoice numbers, billing addresses, line items with quantities and prices",
                    "Extract payment terms, due dates, tax information",
                    "Identify vendor and customer information clearly",
                ],
                "receipt": [
                    "Focus on transaction details, merchant information, payment methods",
                    "Extract itemized purchases with individual prices",
                    "Look for timestamps, receipt numbers, cashier information",
                ],
                "contract": [
                    "Identify parties involved, contract terms, effective dates",
                    "Extract key obligations, payment schedules, termination clauses",
                    "Note signatures, witness information, governing law",
                ],
                "bank_statement": [
                    "Extract account information, transaction history, balances",
                    "Identify transaction types (debits, credits, transfers)",
                    "Note dates, descriptions, running balances",
                ],
            }
            hints.extend(type_hints.get(document_type.lower(), []))

        if file_extension:
            ext_hints = {
                ".pdf": [
                    "May contain multiple pages, check for continuation across pages"
                ],
                ".jpg": [
                    "Image quality may affect OCR accuracy, focus on clear text regions"
                ],
                ".png": ["High-quality image, expect good OCR results"],
                ".docx": ["Structured document with potential formatting cues"],
            }
            hints.extend(ext_hints.get(file_extension.lower(), []))

        return (
            "- " + "\n- ".join(hints)
            if hints
            else "Use general document analysis best practices"
        )

    def generate_prompt(
        self,
        document_text: str,
        schema: Dict[str, Any],
        document_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        model_specific_instructions: Optional[str] = None,
    ) -> str:
        """
        Generate a complete prompt with all placeholders filled

        Args:
            document_text: The extracted text content
            schema: JSON schema for structured output
            document_type: Detected document type for context
            file_extension: File extension for format-specific hints
            model_specific_instructions: Additional model-specific guidance
        """
        try:
            # Prepare schema as formatted JSON
            schema_json = json.dumps(schema, indent=2)

            # Generate context hints
            context_hints = self._generate_context_hints(document_type, file_extension)

            # Prepare placeholders
            placeholders = {
                "document_text": document_text,
                "schema_json": schema_json,
                "context_hints": context_hints,
                "document_type": document_type or "unknown",
                "file_extension": file_extension or "unknown",
            }

            # Always provide the placeholder to avoid format errors
            placeholders["model_instructions"] = model_specific_instructions or ""

            template = self.template
            if model_specific_instructions and "{model_instructions}" not in template:
                template = f"{template}\n\n**Model-Specific Instructions:**\n{{model_instructions}}"

            # Substitute placeholders
            formatted_prompt = template.format(**placeholders)

            logger.debug(f"Generated prompt with {len(formatted_prompt)} characters")
            return formatted_prompt

        except Exception as e:
            logger.error(f"Error generating prompt: {e}")
            # Fallback to simple prompt
            return f"Analyze this document and extract information according to the schema:\n\n{document_text}\n\nSchema: {json.dumps(schema)}"

    def get_model_specific_instructions(self, model_name: str) -> Optional[str]:
        """Get model-specific instructions for optimal performance"""
        model_instructions = {
            # Local Ollama models
            "qwen-vision": "Focus on visual elements and text extraction. Use your strong multilingual capabilities for non-English content.",
            "granite-vision": "Leverage your enterprise document understanding. Pay attention to business document structures and formal language.",
            "gemma": "Use your efficient processing for structured data extraction. Focus on accuracy over verbosity.",
            "llava": "Utilize your strong vision-language understanding. Describe visual elements that provide context.",
            "llama-vision": "Apply your balanced approach to both visual and textual analysis. Consider document layout and formatting cues.",
            # Direct API models
            "mistral-document": "Use your OCR capabilities for image documents. Focus on high-accuracy text extraction before analysis.",
            "gpt4-vision": "Apply your advanced reasoning to complex document structures. Consider implicit information and relationships.",
            # OpenRouter models
            "openrouter-claude": "Apply Claude's exceptional reasoning and analysis capabilities. Focus on nuanced document understanding and context.",
            "openrouter-gpt4-vision": "Leverage GPT-4's advanced vision capabilities for complex document analysis. Consider implicit relationships and context.",
            "openrouter-gemini-flash": "Use Gemini Flash's speed and accuracy for efficient document processing. Balance speed with thoroughness.",
            "openrouter-gemini-pro": "Apply Gemini Pro's advanced reasoning for complex document structures. Consider multi-modal context clues.",
            "openrouter-qwen-vl": "Utilize Qwen's strong multilingual and vision capabilities. Excel at non-English documents and complex layouts.",
            "openrouter-pixtral": "Leverage Pixtral's specialized OCR and document analysis capabilities. Focus on accurate text extraction and structure recognition.",
            "openrouter-llava": "Apply LLaVA's open-source vision-language understanding. Balance visual and textual analysis effectively.",
            # llama.cpp GGUF models
            "qwen2.5-vl": "Apply your exceptional multilingual capabilities (100+ languages) and visual understanding. Excel at extracting structured data from complex document layouts and non-English content.",
            "llama3.2-vision": "Leverage your balanced vision-language capabilities for comprehensive document analysis. Provide thorough analysis of both visual and textual elements with strong reasoning.",
            "olmocr-7b": "Focus on accurate text extraction from document images. Prioritize OCR quality and text layout preservation over general analysis. Extract all visible text content precisely.",
            # Direct API models (new)
            "claude-vision": "Apply your exceptional reasoning and document understanding capabilities. Focus on nuanced analysis, implicit relationships, and comprehensive structured data extraction with high accuracy.",
            "gemini-vision": "Leverage your fast multimodal processing and native JSON capabilities. Provide efficient document analysis with strong visual understanding and structured output generation.",
        }
        return model_instructions.get(model_name)

    def validate_template(self) -> bool:
        """Validate that the template contains required placeholders"""
        required_placeholders = ["{document_text}", "{schema_json}"]
        for placeholder in required_placeholders:
            if placeholder not in self.template:
                logger.error(f"Template missing required placeholder: {placeholder}")
                return False
        return True

    def reload_template(self):
        """Reload the prompt template from file"""
        self.template = self._load_prompt_template()
        logger.info("Prompt template reloaded")


# Global instance
prompt_manager = PromptManager()
