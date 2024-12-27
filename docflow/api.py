from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from enum import Enum
import tempfile
import os
from pathlib import Path
from .processor import DocumentProcessor
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="DocFlow API",
    description="""
    DocFlow is a document processing API that supports:
    * PDF, DOCX, and TXT file processing
    * Metadata extraction
    * Document classification
    * OCR capabilities
    * Multiple AI model support
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a base processor to get available models
processor = DocumentProcessor()

class AIModel(str, Enum):
    """Enum for available AI models"""
    LLAVA = "llava"
    LLAMA = "llama-vision"
    GPT4 = "gpt4-vision"
    GEMINI = "gemini"
    FALLBACK = "fallback"

@app.get("/")
async def root():
    """
    Welcome to DocFlow API
    """
    return {
        "name": "DocFlow API",
        "version": "1.0.0",
        "endpoints": {
            "documentation": "/docs",
            "process": "/process",
            "models": "/models"
        }
    }

@app.get("/models")
async def get_available_models():
    """
    Get list of available AI models
    """
    return {"models": processor.get_supported_models()}

@app.post("/process",
    summary="Process a document",
    response_description="Document metadata and classification results",
    tags=["Document Processing"])
async def process_document(
    file: UploadFile = File(..., description="The document file (PDF, DOCX, or TXT)"),
    use_ocr: bool = Form(default=False, description="Enable OCR processing for documents"),
    include_text: bool = Form(default=False, description="Include extracted text in response"),
    model: AIModel = Form(default=AIModel.LLAVA, description="AI model to use for analysis")
):
    """
    Process a document and extract metadata.

    **Parameters:**
    * file: The document file to process (PDF, DOCX, or TXT)
    * use_ocr: Enable OCR processing for documents (default: false)
    * include_text: Include extracted text in response (default: false)
    * model: AI model to use for analysis (default: llava)

    **Supported File Types:**
    * PDF
    * DOCX
    * TXT

    **Available Models:**
    * llava (default) - LLaVA via Ollama (requires installation)
    * llama-vision - Llama 3.2 Vision via Ollama (requires installation)
    * gpt4-vision - OpenAI's GPT-4 Vision API (requires OPENAI_API_KEY)
    * gemini - Google's Gemini Pro Vision (requires GOOGLE_API_KEY)
    * fallback - Basic text analysis without AI

    **Returns:**
    - document_type: The classified type of the document
    - metadata: Extracted metadata fields
    - text_content: Full extracted text (if include-text is true)
    - ai_analysis: AI model analysis results
    """
    try:
        # Get original file extension
        original_extension = Path(file.filename).suffix.lower()
        if original_extension not in processor.supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {original_extension}. Supported formats: {', '.join(processor.supported_formats)}"
            )

        # Create temporary file with correct extension
        with tempfile.NamedTemporaryFile(suffix=original_extension, delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            # Initialize processor with selected model
            processor_instance = DocumentProcessor(ai_model=model.value)
            result = processor_instance.process_document(temp_path, use_ocr)

            # Remove text_content if not requested
            if not include_text and 'text_content' in result:
                del result['text_content']

            return JSONResponse(content=result)
        finally:
            # Clean up temporary file
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))