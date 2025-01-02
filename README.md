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

Environment variables can be configured in the `.env` file. Here are all available configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| PORT | API server port | 8000 |
| HOST | API server host | 0.0.0.0 |
| PRIMARY_MODEL | Primary AI model to use (llava, llama-vision, gpt4-vision, gemini, or fallback) | llava |
| OLLAMA_HOST | Ollama API host URL | http://localhost:11434 |
| OLLAMA_TIMEOUT | Timeout in seconds for Ollama API calls | 40 |
| OLLAMA_TEMPERATURE | Temperature setting for Ollama models | 0.2 |
| OPENAI_API_KEY | OpenAI API key (required for GPT-4 Vision) | - |
| GOOGLE_API_KEY | Google API key (required for Gemini) | - |
| XAI_API_KEY | xAI API key (required for Grok Vision) | - |
| LOG_LEVEL | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| LOG_FILE | Log file path | docflow.log |
| MAX_FILE_SIZE | Maximum file size in bytes | 10485760 (10MB) |
| ENABLE_OCR | Enable OCR processing for PDFs | true |
| TEMP_DIR | Directory for temporary files | /tmp/docflow |
| DOCFLOW_LOG_LEVEL | Detailed logging level for DocFlow modules | ERROR |
| OLLAMA_LLAVA_MODEL | Model name for LLaVA | llava:latest |
| OLLAMA_LLAMA_VISION_MODEL | Model name for Llama Vision | llama3.2-vision:latest |
| GROK_MODEL | Model name for Grok Vision | grok-2-vision-1212 |
| FALLBACK_CONFIDENCE_THRESHOLD | Confidence threshold for fallback model | 0.6 |

### Model-Specific Requirements

- **GPT-4 Vision**: Requires `OPENAI_API_KEY`
- **Gemini**: Requires `GOOGLE_API_KEY`
- **Grok Vision**: Requires `XAI_API_KEY`
- **LLaVA/Llama Vision**: Requires Ollama to be installed and running locally or at specified `OLLAMA_HOST`
- **Fallback Model**: No specific requirements (always available)

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
