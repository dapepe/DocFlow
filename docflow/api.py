from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from .processor import DocumentProcessor
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="DocFlow API",
    description="Document processing API for extracting metadata and classifying documents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = DocumentProcessor()

@app.post("/process")
async def process_document(
    file: UploadFile = File(...),
    use_ocr: bool = False
):
    """
    Process a document and extract metadata.
    
    Parameters:
    - file: The document file (PDF, DOCX, or TXT)
    - use_ocr: Whether to use OCR for processing (optional)
    
    Returns:
    - Document metadata and classification results
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            result = processor.process_document(temp_path, use_ocr)
            return result
        finally:
            # Clean up temporary file
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
