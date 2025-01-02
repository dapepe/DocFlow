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
        # Validate and get the requested model
        available_models = ModelRegistry.list_models()
        if model not in available_models:
            logger.warning(f"Requested model '{model}' not found in available models: {list(available_models.keys())}")
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' is not available. Available models: {list(available_models.keys())}"
            )

        # Try to get requested model
        model_class = ModelRegistry.get_model(model)
        if not model_class:
            logger.error(f"Failed to get model class for '{model}'")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize model '{model}'"
            )

        # Check model availability before processing
        try:
            if not model_class.is_available():
                logger.error(f"Model '{model}' is not available")
                raise HTTPException(
                    status_code=503,
                    detail=f"Model '{model}' is currently not available"
                )
        except Exception as e:
            logger.error(f"Error checking availability for model '{model}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error checking model availability: {str(e)}"
            )

        # Create model instance
        try:
            model_instance = model_class()
        except Exception as e:
            logger.error(f"Error creating instance of model '{model}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize model '{model}': {str(e)}"
            )

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
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Model processing failed: {error_msg}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Model processing failed: {error_msg}"
                    )

                return JSONResponse(content=result)
            finally:
                os.unlink(temp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))