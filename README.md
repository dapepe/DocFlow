# DocFlow Document Processor

DocFlow is a powerful document processing tool that supports PDF, DOCX, and TXT files with features for metadata extraction, document classification, and OCR capabilities.

## Features

- Document classification based on content
- Metadata extraction (dates, amounts, invoice numbers, etc.)
- OCR support for PDF files
- REST API with FastAPI
- Command-line interface
- Rich console output

## Requirements

- Python 3.11+
- Dependencies are listed in requirements.txt and will be installed automatically when you run the project

## Getting started

### Run locally with Python

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
