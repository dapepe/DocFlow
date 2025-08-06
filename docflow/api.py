from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from enum import Enum
import tempfile
import os
import time
from pathlib import Path
from .models import ModelRegistry
from .processor import DocumentProcessor
import logging
from typing import List
from .performance_optimizer import get_performance_report, batch_processor
from .prompt_manager import prompt_manager

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

@app.get("/performance")
async def get_performance_stats():
    """Get performance statistics and metrics"""
    try:
        return get_performance_report()
    except Exception as e:
        logger.error(f"Error retrieving performance stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving performance statistics: {str(e)}"
        )

@app.post("/process")
async def process_document(
    file: UploadFile = File(...),
    use_ocr: bool = Form(default=False),
    include_text: bool = Form(default=False),
    convert_to_img: bool = Form(default=False),
    model: str = Form(default="qwen-vision")
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

@app.post("/batch-process")
async def batch_process_documents(
    files: List[UploadFile] = File(...),
    use_ocr: bool = Form(default=False),
    model: str = Form(default="qwen-vision")
):
    """Process multiple documents in batch"""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch")
    
    try:
        available_models = ModelRegistry.list_models()
        if model not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' is not available. Available models: {list(available_models.keys())}"
            )

        temp_files = []
        documents = []
        
        try:
            # Save all uploaded files
            for i, file in enumerate(files):
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
                    content = await file.read()
                    temp_file.write(content)
                    temp_files.append(temp_file.name)
                    
                    documents.append({
                        'id': f'batch_doc_{i}',
                        'file_path': temp_file.name,
                        'use_ocr': use_ocr,
                        'original_filename': file.filename
                    })
            
            # Process in batch
            def single_process(file_path, use_ocr, **kwargs):
                processor = DocumentProcessor(ai_model=model)
                return processor.process_document(file_path, use_ocr)
            
            results = batch_processor.process_batch(documents, single_process)
            
            # Add original filenames to results
            for i, result in enumerate(results):
                result['original_filename'] = documents[i]['original_filename']
            
            return {
                'batch_id': f'batch_{int(time.time())}',
                'total_documents': len(files),
                'results': results,
                'processing_summary': {
                    'successful': sum(1 for r in results if r.get('success', True)),
                    'failed': sum(1 for r in results if not r.get('success', True))
                }
            }
            
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/prompt")
async def get_prompt_template():
    """Get the current prompt template"""
    try:
        return {
            'template': prompt_manager.template,
            'is_valid': prompt_manager.validate_template(),
            'file_path': prompt_manager.prompt_file
        }
    except Exception as e:
        logger.error(f"Error retrieving prompt template: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving prompt template: {str(e)}"
        )

@app.post("/prompt/reload")
async def reload_prompt_template():
    """Reload the prompt template from file"""
    try:
        prompt_manager.reload_template()
        return {
            'status': 'success',
            'message': 'Prompt template reloaded successfully',
            'is_valid': prompt_manager.validate_template()
        }
    except Exception as e:
        logger.error(f"Error reloading prompt template: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reloading prompt template: {str(e)}"
        )