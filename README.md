# DocFlow Document Processor

DocFlow is an advanced document processing system that supports PDF, DOCX, TXT, and image files with AI-powered features for metadata extraction, document classification, and OCR capabilities. Features configurable prompts, multiple AI model support, and enterprise-grade document analysis.

## 🚀 Features

### Core Capabilities
- **Multi-format Support**: PDF, DOCX, TXT, JPG, PNG image files
- **AI-Powered Analysis**: Advanced document classification and metadata extraction
- **OCR Integration**: Built-in OCR for image documents and scanned PDFs
- **Configurable Prompts**: Customizable prompt templates with placeholder support
- **REST API**: FastAPI-based with automatic documentation
- **Command-line Interface**: Rich console output with verbose logging
- **Enterprise Ready**: Docker support, comprehensive logging, error handling

### AI Model Support
- **🎯 Qwen2.5 Vision** (qwen-vision / qwen2.5-vl) - Multilingual vision model (Ollama or llama.cpp)
- **💎 Granite3.2 Vision** (granite-vision) - IBM's enterprise document understanding
- **⚡ Gemma3** (gemma) - Google's efficient 12B parameter model
- **🦙 LLaVA** (llava) - Popular vision-language model
- **🦙 Llama Vision** (llama-vision / llama3.2-vision) - Meta's balanced vision-text analysis
- **🔬 Mistral Document AI** (mistral-document) - Advanced OCR and document processing
- **🧠 GPT-4 Vision** (gpt4-vision) - OpenAI's premier vision model
- **⚡ Claude 3.7 Sonnet** (claude-vision) - Anthropic's latest reasoning model (Direct API)
- **🏃 Gemini 2.0 Flash** (gemini-vision) - Google's ultra-fast multimodal model (Direct API)
- **🔍 olmOCR** (olmocr-7b) - Specialized OCR model for accurate text extraction (llama.cpp)
- **📄 Docling** (docling-local) - Advanced layout analysis and table extraction
- **⚙️ Fallback Model** (fallback) - Rule-based processing for offline use

## 📋 Requirements

- **Python**: 3.11+
- **System Dependencies**:
  - Poppler (PDF processing)
  - Pillow (image processing)
  - CMake & Build Tools (for llama.cpp)
- **AI Services** (optional):
  - Ollama (local models)
  - llama.cpp (embedded GGUF models)
  - OpenAI / Anthropic / Google / Mistral APIs

## ⚙️ Configuration

### Environment Variables

Create a `.env` file from `env.template.txt`:

| Variable | Description | Default |
|----------|-------------|---------|
| **API Configuration** |
| `PORT` | API server port | 8000 |
| `HOST` | API server host | 0.0.0.0 |
| `PRIMARY_MODEL` | Default AI model | qwen-vision |
| **Ollama Models** |
| `OLLAMA_HOST` | Ollama API host URL | http://localhost:11434 |
| `OLLAMA_TIMEOUT` | Request timeout in seconds | 60 |
| `OLLAMA_TEMPERATURE` | Model temperature | 0.2 |
| `OLLAMA_QWEN_VISION_MODEL` | Qwen model name | qwen2.5vl:7b |
| `OLLAMA_GRANITE_VISION_MODEL` | Granite model name | granite3.2-vision:latest |
| `OLLAMA_GEMMA_MODEL` | Gemma model name | gemma3:12b |
| `OLLAMA_LLAVA_MODEL` | LLaVA model name | llava:latest |
| `OLLAMA_LLAMA_VISION_MODEL` | Llama Vision model name | llama3.2-vision:latest |
| **API Keys** |
| `OPENAI_API_KEY` | OpenAI API key (for GPT-4) | - |
| `MISTRAL_API_KEY` | Mistral API key | - |
| `GOOGLE_API_KEY` | Google API key (for Gemini) | - |
| **Advanced Configuration** |
| `DOCFLOW_SCHEMA_PATH` | JSON schema file path | config/schema.json |
| `DOCFLOW_LOG_LEVEL` | Logging level | ERROR |
| `MAX_FILE_SIZE` | Max file size (bytes) | 10485760 (10MB) |

### Configurable Prompts

DocFlow uses a sophisticated prompt system with `config/prompt.txt` supporting:

**Available Placeholders:**
- `{document_text}` - Extracted document content
- `{schema_json}` - JSON schema for structured output  
- `{context_hints}` - Document-type specific analysis hints
- `{document_type}` - Detected document type
- `{file_extension}` - File format for processing hints
- `{model_instructions}` - Model-specific optimization instructions

**Features:**
- Document-type specific context hints (invoice, receipt, contract, etc.)
- Model-specific instructions for optimal performance
- File-format specific processing guidance
- Advanced validation and quality standards

### Document Rules

Configure document classification in `config/rules.yaml`:

```yaml
rules:
  invoice:
    keywords: ["invoice", "bill", "payment due"]
    metadata_fields:
      invoice_number:
        pattern: "Invoice No\\.?:\\s*([A-Za-z0-9-/]+)"
        type: "String"
      total_amount:
        pattern: "Total[\\s:]+\\$?([0-9,\\.]+)"
        type: "Float"
      date:
        pattern: "Date[\\s:]+([0-9/\\-]+)"
        type: "Date"
```

## 🚀 Getting Started

### 1. System Dependencies

```bash
# macOS
brew install poppler

# Windows  
choco install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# CentOS/RHEL
sudo yum install poppler-utils
```

### 2. Python Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp env.template.txt .env

# Edit configuration
nano .env
```

### 3. AI Model Setup

**Option A: llama.cpp (Recommended for Local Use)**
DocFlow now supports direct GGUF inference via llama.cpp, which is faster and lighter than Ollama.

1. Download GGUF models (see `env.template.txt` for links).
2. Configure paths in `.env`:
   ```bash
   LLAMA_CPP_QWEN25_VL_PATH=/path/to/qwen2.5-vl.gguf
   LLAMA_CPP_LLAMA32_VISION_PATH=/path/to/llama3.2-vision.gguf
   ```
3. DocFlow will auto-detect GPU and optimize settings.

**Option B: Ollama (Alternative Local)**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull qwen2.5vl:7b
ollama pull granite3.2-vision:latest
```

**Option C: Cloud APIs (Best Performance)**
- Add API keys to `.env` for OpenAI, Anthropic, Google, Mistral, or OpenRouter.

### 4. Run the Application

```bash
# Validate configuration
python main.py config

# Run benchmarks
python main.py benchmark --document test.pdf --models qwen2.5-vl claude-vision

# Start API server
python main.py serve --host 0.0.0.0 --port 8000
```

## 🔧 Usage

### REST API

Access comprehensive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Key Endpoints:**
```bash
# Get available models
GET /models

# Process document
POST /process
  - file: document file
  - model: AI model choice
  - use_ocr: enable OCR
  - include_text: return extracted text
```

**Example API Call:**
```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@invoice.pdf" \
  -F "model=qwen-vision" \
  -F "use_ocr=true"
```

### Command Line Interface

**Process Documents:**
```bash
# Basic processing
./process.sh document.pdf

# With specific model
./process.sh document.pdf --model granite-vision

# Enable OCR and save results
./process.sh scan.jpg --use-ocr --output results.json

# Verbose logging
./process.sh contract.pdf --model mistral-document --verbose
```

**Available Models:**
- `qwen-vision` (Default) - Qwen2.5VL multimodal model
- `granite-vision` - IBM Granite3.2 enterprise model
- `gemma` - Google Gemma3 12B efficient model
- `llava` - Popular vision-language model
- `llama-vision` - Meta Llama3.2 vision model
- `mistral-document` - Mistral with OCR capabilities
- `gpt4-vision` - OpenAI GPT-4 Vision (requires API key)
- `fallback` - Rule-based processing (offline)

**Advanced Options:**
```bash
# Save extracted text separately
./process.sh document.pdf --save-text extracted.txt

# Include full text in output
./process.sh document.pdf --include-text

# Custom output path
./process.sh document.pdf --output analysis.json
```

## 🐳 Docker Deployment

### Standard Docker

```bash
# Build image
docker build -t docflow .

# Run container
docker run -p 8000:8000 \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -v ./documents:/app/documents \
  docflow
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🏗️ Architecture

### Model Registry System
Dynamic model loading with automatic availability detection:

```python
from docflow.models import ModelRegistry

# List available models
models = ModelRegistry.list_models()

# Get specific model
model = ModelRegistry.get_model("qwen-vision")
```

### Prompt Management
Centralized prompt system with advanced templating:

```python
from docflow.prompt_manager import prompt_manager

# Generate enhanced prompt
prompt = prompt_manager.generate_prompt(
    document_text=text,
    schema=schema,
    document_type="invoice",
    model_specific_instructions="Focus on accuracy"
)
```

### Processing Pipeline
1. **Document Upload** → File validation and temporary storage
2. **Text Extraction** → Format-specific text extraction with OCR
3. **Document Classification** → Rule-based initial classification
4. **AI Analysis** → Selected model processes with enhanced prompts
5. **Response Processing** → Validation and structured output
6. **Result Return** → JSON response with metadata and analysis

## 🔍 Advanced Features

### Response Validation
- JSON schema validation
- Data type checking
- Cross-field consistency validation
- Confidence scoring

### Performance Optimizations
- Concurrent model processing
- Intelligent caching
- Request batching for APIs
- Optimized prompt templates

### Error Handling
- Graceful model fallbacks
- Retry mechanisms with backoff
- Comprehensive error logging
- User-friendly error messages

### Monitoring & Observability
- Structured logging with context
- Performance metrics
- Model availability monitoring
- Request/response tracing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README and API docs
- **Issues**: Report bugs via GitHub Issues  
- **Questions**: Use GitHub Discussions
- **Enterprise**: Contact for enterprise support

---

**Built with ❤️ using FastAPI, Ollama, and modern AI models**