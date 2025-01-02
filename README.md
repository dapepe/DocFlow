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
- Dependencies are listed in requirements.txt and will be installed automatically when you run the project
- For AI models:
  - OpenAI API key for GPT-4 Vision
  - xAI API key for Grok Vision
  - Ollama server for LLaVA and Llama Vision

## Getting started

### Run locally with Python

1. Install system dependencies and configure AI models:

**MacOS**

```bash
brew install poppler
```

**Windows**

```bash
choco install poppler
```

**Linux**

```bash
sudo apt-get install poppler-utils
```


2. Clone the repository and install Python dependencies:

```bash
git clone https://github.com/your-repo/docflow.git
cd docflow
```

3. I nstall Python dependencies:

```bash
pip install -r requirements.txt
```  

4. Configure your AI models in config/models.yaml:

```yaml
default_model: gpt4-vision
fallback_model: llama-vision
models:
  gpt4-vision:
    enabled: true
    api_key: your_openai_key
  grok-vision:
    enabled: true
    api_key: your_xai_key
  llama-vision:
    enabled: true
    ollama_url: http://localhost:11434
  llava:
    enabled: true
    ollama_url: http://localhost:11434
```

5. Run the project:

```bash
./serve.sh # To start the API server
./process.sh path/to/document.pdf --ocr # To process a document
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

### Getting Started on Replit

1. Fork this repl to your Replit account
2. The project will automatically install dependencies
3. Click the "Run" button to start both:
   - The API server (available on port 8000)
   - The CLI demo processing a sample invoice

The project is automatically configured to run in Replit's environment with:
- Automatic dependency management
- Parallel execution of API and CLI components
- Port forwarding for the API server
- Environment configuration via Replit's built-in tools

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
