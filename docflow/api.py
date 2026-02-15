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
import structlog
from typing import List
from .performance_optimizer import get_performance_report, batch_processor
from .prompt_manager import prompt_manager
from .logging_config import configure_logging
from .middleware import RequestIDMiddleware

# Configure logging on module load
configure_logging()
logger = structlog.get_logger(__name__)

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
    redoc_url="/redoc",
)

# Add RequestIDMiddleware first (outer layer)
app.add_middleware(RequestIDMiddleware)

# Add CORSMiddleware (inner layer)
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
            "models": "/models",
        },
    }


@app.get("/models")
async def get_available_models():
    """Get list of available AI models"""
    try:
        available_models = ModelRegistry.list_models()
        if not available_models:
            logger.warning(
                "no_models_available", action="ensuring_fallback_registration"
            )
            fallback_model = ModelRegistry.get_model("fallback")
            if fallback_model:
                available_models = {"fallback": fallback_model.description}
            else:
                raise HTTPException(
                    status_code=500,
                    detail="No models available and fallback model initialization failed",
                )
        logger.info("models_retrieved", model_count=len(available_models))
        return {"models": available_models}
    except Exception as e:
        logger.error("error_listing_models", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving available models: {str(e)}"
        )


@app.get("/performance")
async def get_performance_stats():
    """Get performance statistics and metrics"""
    try:
        logger.info("performance_stats_requested")
        report = get_performance_report()
        logger.info("performance_stats_retrieved")
        return report
    except Exception as e:
        logger.error("error_retrieving_performance_stats", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving performance statistics: {str(e)}"
        )


@app.post("/process")
async def process_document(
    file: UploadFile = File(...),
    use_ocr: bool = Form(default=False),
    include_text: bool = Form(default=False),
    convert_to_img: bool = Form(default=False),
    model: str = Form(default="qwen-vision"),
):
    """Process a document and extract metadata"""
    try:
        logger.info(
            "processing_request_received",
            filename=file.filename,
            model=model,
            use_ocr=use_ocr,
        )

        # Validate and get the requested model
        available_models = ModelRegistry.list_models()
        if model not in available_models:
            logger.warning(
                "model_not_found",
                requested_model=model,
                available_models=list(available_models.keys()),
            )
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' is not available. Available models: {list(available_models.keys())}",
            )

        # Save uploaded file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

            try:
                # Initialize document processor with specified model
                processor = DocumentProcessor(ai_model=model)

                # Process the document
                result = await processor.process_document_async(
                    file_path=temp_path, use_ocr=use_ocr, convert_to_img=convert_to_img
                )

                # Remove text content if not requested
                if not include_text:
                    result.pop("text_content", None)

                # Check for processing success
                ai_analysis = result.get("ai_analysis", {})
                if not ai_analysis.get("success", False):
                    error_msg = ai_analysis.get(
                        "error", "Unknown error in AI processing"
                    )
                    logger.error(
                        "ai_processing_failed", error=error_msg, filename=file.filename
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Document processing failed: {error_msg}",
                    )

                logger.info("processing_completed", filename=file.filename, model=model)
                return JSONResponse(content=result)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "error_processing_document",
                    error=str(e),
                    filename=file.filename,
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=500, detail=f"Error processing document: {str(e)}"
                )
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(
                        "failed_cleanup_temp_file", temp_path=temp_path, error=str(e)
                    )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("unexpected_error_process_document", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch-process")
async def batch_process_documents(
    files: List[UploadFile] = File(...),
    use_ocr: bool = Form(default=False),
    model: str = Form(default="qwen-vision"),
):
    """Process multiple documents in batch"""
    if len(files) > 10:
        logger.warning("batch_size_exceeded", file_count=len(files), max_allowed=10)
        raise HTTPException(
            status_code=400, detail="Maximum 10 files allowed per batch"
        )

    try:
        logger.info("batch_processing_started", file_count=len(files), model=model)

        available_models = ModelRegistry.list_models()
        if model not in available_models:
            logger.warning("model_not_found_batch", requested_model=model)
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' is not available. Available models: {list(available_models.keys())}",
            )

        temp_files = []
        documents = []

        try:
            # Save all uploaded files
            for i, file in enumerate(files):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=Path(file.filename).suffix
                ) as temp_file:
                    content = await file.read()
                    temp_file.write(content)
                    temp_files.append(temp_file.name)

                    documents.append(
                        {
                            "id": f"batch_doc_{i}",
                            "file_path": temp_file.name,
                            "use_ocr": use_ocr,
                            "original_filename": file.filename,
                        }
                    )

            # Process in batch
            file_paths = [doc["file_path"] for doc in documents]

            # Use async batch processor
            processor = DocumentProcessor(ai_model=model)
            results = await processor.process_batch_async(
                file_paths=file_paths,
                use_ocr=use_ocr,
                max_concurrency=4,  # Could make this configurable
            )

            # Add original filenames to results (results order matches input)
            for i, result in enumerate(results):
                result["original_filename"] = documents[i]["original_filename"]

            successful = sum(1 for r in results if r.get("success", True))
            failed = sum(1 for r in results if not r.get("success", True))

            logger.info(
                "batch_processing_completed",
                file_count=len(files),
                successful=successful,
                failed=failed,
            )

            return {
                "batch_id": f"batch_{int(time.time())}",
                "total_documents": len(files),
                "results": results,
                "processing_summary": {
                    "successful": successful,
                    "failed": failed,
                },
            }

        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(
                        "failed_cleanup_temp_file_batch",
                        temp_path=temp_file,
                        error=str(e),
                    )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("batch_processing_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/prompt")
async def get_prompt_template():
    """Get the current prompt template"""
    try:
        logger.info("prompt_template_requested")
        is_valid = prompt_manager.validate_template()
        logger.info("prompt_template_retrieved", is_valid=is_valid)
        return {
            "template": prompt_manager.template,
            "is_valid": is_valid,
            "file_path": prompt_manager.prompt_file,
        }
    except Exception as e:
        logger.error("error_retrieving_prompt_template", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving prompt template: {str(e)}"
        )


@app.post("/prompt/reload")
async def reload_prompt_template():
    """Reload the prompt template from file"""
    try:
        logger.info("prompt_template_reload_requested")
        prompt_manager.reload_template()
        is_valid = prompt_manager.validate_template()
        logger.info("prompt_template_reloaded", is_valid=is_valid)
        return {
            "status": "success",
            "message": "Prompt template reloaded successfully",
            "is_valid": is_valid,
        }
    except Exception as e:
        logger.error("error_reloading_prompt_template", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error reloading prompt template: {str(e)}"
        )
