from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from enum import Enum
import tempfile
import os
from pathlib import Path
from .models import ModelRegistry
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

class AIModel(str, Enum):
    """Enum for available AI models"""
    def __new__(cls):
        # Dynamically create enum values from registered models
        values = list(ModelRegistry.list_models().keys())
        # Ensure fallback is always available
        if "fallback" not in values:
            values.append("fallback")
        return str.__new__(cls, values[0])

@app.get("/")
async def root():
    """Welcome to DocFlow API"""
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
    """Get list of available AI models"""
    return {"models": ModelRegistry.list_models()}

@app.post("/process")
async def process_document(
    file: UploadFile = File(...),
    use_ocr: bool = Form(default=False),
    include_text: bool = Form(default=False),
    convert_to_img: bool = Form(default=False),
    model: str = Form(default="llama-vision")
):
    """Process a document and extract metadata"""
    try:
        # Validate model choice
        model_class = ModelRegistry.get_model(model)
        if not model_class:
            logger.warning(f"Model {model} not found, falling back to fallback model")
            model_class = ModelRegistry.get_model("fallback")

        if not model_class.is_available():
            raise HTTPException(
                status_code=400,
                detail=f"Model {model} is not available in the current environment"
            )

        # Create model instance
        model_instance = model_class()

        # Process document
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

            try:
                result = model_instance.extract_information(
                    text="",  # Text extraction will be handled by the processor
                    image_path=temp_path if convert_to_img else None
                )

                if not include_text:
                    result.pop('text_content', None)

                return JSONResponse(content=result)
            finally:
                os.unlink(temp_path)

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))