# llama.cpp Setup Guide

DocFlow v2.0 introduces native support for `llama.cpp`, allowing you to run quantized GGUF models locally with high performance and low overhead.

## Why llama.cpp?

- **No Daemon Required**: Runs directly within the DocFlow process.
- **Lower Memory Usage**: Uses optimized GGUF format with quantization (Q4_K_M recommended).
- **Auto-GPU Offload**: Automatically detects NVIDIA GPUs and offloads layers for speed.
- **Apple Silicon Support**: Native Metal acceleration on macOS.

## Installation

The `llama-cpp-python` dependency is included in `requirements.txt`, but it requires build tools to compile the C++ backend.

### Prerequisites

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install build-essential cmake
```

**macOS:**
```bash
xcode-select --install
```

**Windows:**
- Install [Visual Studio Community](https://visualstudio.microsoft.com/vs/community/) with C++ development tools.
- Install [CMake](https://cmake.org/download/).

### Installing with Hardware Acceleration

**NVIDIA GPU (CUDA):**
```bash
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir
```

**Apple Silicon (Metal):**
```bash
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir
```

**CPU Only:**
```bash
pip install llama-cpp-python
```

## Model Setup

1. **Download GGUF Models**
   
   We recommend the following quantized models (Q4_K_M offers best balance):

   - **Qwen2.5-VL 7B** (Best All-rounder):
     [Download from HuggingFace](https://huggingface.co/bartowski/Qwen2.5-VL-7B-Instruct-GGUF)
   
   - **Llama 3.2 Vision 11B** (Strong Reasoning):
     [Download from HuggingFace](https://huggingface.co/bartowski/Llama-3.2-11B-Vision-Instruct-GGUF)
   
   - **olmOCR 7B** (Specialized OCR):
     [Download from HuggingFace](https://huggingface.co/allenai/olmOCR-7B-0225-preview-GGUF)

2. **Configure Paths**

   Edit your `.env` file to point to the downloaded `.gguf` files:

   ```env
   # Enable llama.cpp verbose logging if needed
   LLAMA_CPP_VERBOSE=false
   
   # Auto-detect VRAM and offload layers (Recommended)
   LLAMA_CPP_AUTO_GPU_LAYERS=true
   
   # Model Paths
   LLAMA_CPP_QWEN25_VL_PATH=/home/user/models/qwen2.5-vl-7b-instruct-q4_k_m.gguf
   LLAMA_CPP_LLAMA32_VISION_PATH=/home/user/models/llama-3.2-11b-vision-instruct-q4_k_m.gguf
   LLAMA_CPP_OLMOCR_PATH=/home/user/models/olmOCR-7b-q4_k_m.gguf
   ```

## Verification

Run the config check command to verify hardware detection and model paths:

```bash
python main.py config
```

You should see output indicating your VRAM/RAM detection and model status.

## Troubleshooting

- **"Failed to load model"**: Ensure the path is correct and the file is a valid GGUF.
- **"Out of memory"**: Try a smaller quantization (e.g., Q4_K_S) or reduce context window (`LLAMA_CPP_N_CTX=4096`).
- **Slow performance**: Ensure GPU offloading is working. Check logs for `BLAS = 1`.
