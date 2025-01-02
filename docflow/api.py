from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from enum import Enum
import tempfile
import os
from pathlib import Path
from .models import ModelRegistry
from .processor import DocumentProcessor
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

        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

            try:
                # Initialize document processor with specified model
                processor = DocumentProcessor(ai_model=model)

                # Process the document
                result = processor.process_document(
                    file_path=temp_path,
                    use_ocr=use_ocr,
                    convert_to_img=convert_to_img
                )

                # Remove text content if not requested
                if not include_text:
                    result.pop('text_content', None)

                # Check for processing success
                ai_analysis = result.get('ai_analysis', {})
                if not ai_analysis.get('success', False):
                    error_msg = ai_analysis.get('error', 'Unknown error in AI processing')
                    logger.error(f"AI processing failed: {error_msg}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Document processing failed: {error_msg}"
                    )

                return JSONResponse(content=result)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing document: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing document: {str(e)}"
                )
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in process_document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))