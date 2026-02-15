# Model Comparison & Benchmarks

This guide compares the supported AI models in DocFlow to help you choose the right one for your use case.

## Model Tier List

| Tier | Models | Best For | Pros | Cons |
|------|--------|----------|------|------|
| **S-Tier** | Claude 3.7 Sonnet, GPT-4 Vision, Gemini 2.0 Pro | Complex Reasoning, Handwriting, Financial Reports | Highest Accuracy, Best Reasoning | Expensive, API Latency |
| **A-Tier** | Qwen2.5-VL, Llama 3.2 Vision | General Documents, Receipts, Invoices | Fast, Local (Free), Good Accuracy | Requires Hardware (VRAM) |
| **B-Tier** | olmOCR, Docling | Raw Text Extraction, Tables | Perfect Layout/OCR | No Reasoning/Analysis |
| **C-Tier** | Gemma 3, LLaVA | Simple Tasks, Summaries | Very Fast, Low Memory | Lower Accuracy, Hallucinations |

## Recommended Models by Use Case

### 1. Invoices & Receipts
**Winner:** `claude-vision` or `qwen2.5-vl`
- **Why:** Requires precise number extraction and table understanding.
- **Local Option:** `qwen2.5-vl` (via llama.cpp)

### 2. Financial Reports (Tables)
**Winner:** `docling-local` + `claude-vision`
- **Why:** Docling extracts table structures perfectly; Claude analyzes the content.
- **Workflow:** Use Docling for layout, then pass text to Claude.

### 3. Handwritten Notes
**Winner:** `olmocr-7b` or `gemini-vision`
- **Why:** Specialized OCR training (olmOCR) or massive multimodal training (Gemini).

### 4. High-Volume Batch Processing
**Winner:** `gemini-vision` (Flash)
- **Why:** Extremely fast, low cost, huge context window.

## Benchmark Results (Sample)

*Benchmarks run on NVIDIA RTX 4090 (Local) and Standard Fiber (API)*

| Model | Provider | Type | Avg Time | Success Rate |
|-------|----------|------|----------|--------------|
| **Gemini 2.0 Flash** | Google API | Cloud | 1.2s | 99% |
| **Qwen2.5-VL (Q4)** | llama.cpp | Local | 2.5s | 95% |
| **Llama 3.2 Vision (Q4)** | llama.cpp | Local | 3.1s | 92% |
| **Claude 3.7 Sonnet** | Anthropic API | Cloud | 4.5s | 100% |
| **olmOCR 7B** | llama.cpp | Local | 3.8s | 98% (Text only) |

## Running Your Own Benchmarks

You can benchmark models against your specific documents using the CLI:

```bash
python main.py benchmark --document invoice.pdf --models qwen2.5-vl claude-vision --iterations 3
```

This will run each model 3 times against `invoice.pdf` and report average latency and success rates.
