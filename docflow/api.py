from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

processor = DocumentProcessor()

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
            "process": "/process"
        }
    }

@app.post("/process", 
    summary="Process a document",
    response_description="Document metadata and classification results",
    tags=["Document Processing"])
async def process_document(
    file: UploadFile = File(..., description="The document file (PDF, DOCX, or TXT)"),
    use_ocr: bool = File(False, description="Whether to use OCR for processing")
):
    """
    Process a document and extract metadata.

    **Features:**
    * Document classification
    * Metadata extraction
    * OCR processing (optional)

    **Supported File Types:**
    * PDF
    * DOCX
    * TXT

    **Returns:**
    - document_type: The classified type of the document
    - metadata: Extracted metadata fields
    - text_length: Length of the extracted text
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
            result = processor.process_document(temp_path, use_ocr)
            return JSONResponse(content=result)
        finally:
            # Clean up temporary file
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))