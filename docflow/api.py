from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from enum import Enum
import tempfile
import os
from pathlib import Path
from .models import ModelRegistry
import logging
from typing import List

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
    """Dynamic Enum for available AI models"""
    def __new__(cls):
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
    try:
        available_models = ModelRegistry.list_models()
        if not available_models:
            logger.warning("No models available, ensuring fallback model is registered")
            # If no models are available, ensure at least fallback is available
            fallback_model = ModelRegistry.get_model("fallback")
            if fallback_model:
                available_models = {"fallback": fallback_model.description}
            else:
                raise HTTPException(
                    status_code=500,
                    detail="No models available and fallback model initialization failed"
                )
        return {"models": available_models}
    except Exception as e:
        logger.error(f"Error listing available models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving available models: {str(e)}"
        )

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
        # Get all available models
        available_models = ModelRegistry.list_models()
        if not available_models:
            logger.warning("No models available, falling back to fallback model")
            model = "fallback"

        # Try to get requested model
        model_class = ModelRegistry.get_model(model)
        if not model_class:
            logger.warning(f"Model {model} not found, falling back to fallback model")
            model_class = ModelRegistry.get_model("fallback")
            if not model_class:
                raise HTTPException(
                    status_code=500,
                    detail="Fallback model initialization failed"
                )

        # Check model availability
        try:
            if not model_class.is_available():
                logger.warning(f"Model {model} is not available, falling back to fallback model")
                model_class = ModelRegistry.get_model("fallback")
                if not model_class or not model_class.is_available():
                    raise HTTPException(
                        status_code=500,
                        detail="No available models found, including fallback"
                    )
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            model_class = ModelRegistry.get_model("fallback")
            if not model_class or not model_class.is_available():
                raise HTTPException(
                    status_code=500,
                    detail=f"Model availability check failed and fallback model is not available: {str(e)}"
                )

        # Create model instance with proper error handling
        try:
            model_instance = model_class()
        except Exception as e:
            logger.error(f"Error creating model instance: {e}")
            model_class = ModelRegistry.get_model("fallback")
            if not model_class:
                raise HTTPException(
                    status_code=500,
                    detail=f"Model initialization failed and fallback model is not available: {str(e)}"
                )
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

                if not result.get('success', False):
                    logger.warning(f"Model processing failed: {result.get('error', 'Unknown error')}")
                    # Try fallback model if primary model fails
                    fallback_model = ModelRegistry.get_model("fallback")()
                    result = fallback_model.extract_information(
                        text="",
                        image_path=temp_path if convert_to_img else None
                    )
                    if not result.get('success', False):
                        raise HTTPException(
                            status_code=500,
                            detail=f"Both primary and fallback model processing failed: {result.get('error', 'Unknown error')}"
                        )

                return JSONResponse(content=result)
            finally:
                os.unlink(temp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))