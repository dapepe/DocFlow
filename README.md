
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

## Getting Started on Replit

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
```

Start the API server manually:
```bash
python main.py serve --port 8000
```

## Configuration

- Document processing rules: `config/rules.yaml`
- Logging configuration: `config/logging.yaml`

## Project Structure

```
├── config/
│   ├── default_rules.yaml   # Default processing rules
│   ├── logging.yaml         # Logging configuration
│   └── rules.yaml          # Custom processing rules
├── docflow/                 # Main package
│   ├── api.py              # FastAPI implementation
│   ├── cli.py              # CLI implementation
│   └── processor.py        # Document processing logic
└── main.py                 # Entry point
```

## Example Document Processing

```bash
python main.py process test_invoice.txt
```

This will extract metadata and classify the document, displaying results in a formatted table.
