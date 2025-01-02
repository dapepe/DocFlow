# DocFlow Document Processor

DocFlow is an advanced document processing system that supports PDF, DOCX, and TXT files with AI-powered features for metadata extraction, document classification, and OCR capabilities.

## Features

- AI-powered document classification using multiple model providers
- Metadata extraction (dates, amounts, invoice numbers, etc.)
- OCR support for PDF files
- REST API with FastAPI
- Command-line interface
- Rich console output
- Multiple AI model support:
  - GPT-4 Vision
  - Grok Vision
  - LLaVA
  - Llama Vision
  - Fallback model for offline use
- Configurable model selection and fallback behavior

## Requirements

- Python 3.11+
- System dependencies:
  - Poppler (for PDF processing)
  - Pillow (for image processing)
- Python dependencies (see requirements.txt):
  - Core: fastapi, uvicorn, click, rich
  - Document processing: pypdf2, python-docx, pdf2image
  - AI models: openai, ollama, google-generativeai
  - Utilities: pyyaml, python-dateutil, trafilatura

## Configuration

### Logging

Logging is configured in `config/logging.yaml` with:
- Console and file output
- Debug level for docflow modules
- Standard format with timestamps

### Document Rules

Document processing rules are defined in `config/rules.yaml` with:
- Document type detection based on keywords
- Metadata fields to extract for each document type
- Supported document types: invoice, receipt, contract

## Getting Started

1. Install system dependencies:

```bash
# MacOS
brew install poppler

# Windows
choco install poppler

# Linux
sudo apt-get install poppler-utils
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Configure AI models in `config/models.yaml` (see example below)

4. Run the application:

```bash
# Start API server
uvicorn docflow.api:app --reload

# Process document via CLI
python main.py process path/to/document.pdf --ocr
```

### Run with Docker

Running with Docker:

```bash
docker build -t docflow .
```

Run the Docker Container

```bash
docker run -p 8000:8000 docflow
```

Run as service with Docker Compose:

```bash
docker-compose up
```

## Usage

### REST API

The API server starts automatically and is available at port 8000. Access the API documentation at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

Example API endpoints:
- `GET /` - API information
- `POST /process` - Process documents

### Command Line Interface

Process a single document:
```bash
python main.py process path/to/document.pdf --ocr
