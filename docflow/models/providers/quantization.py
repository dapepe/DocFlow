"""
Quantization and Hardware Detection Utilities

Helper functions to detect available VRAM/RAM and suggest optimal
quantization levels for GGUF models.
"""

import os
import shutil
import structlog
from typing import Dict, Any, Optional, Tuple

logger = structlog.get_logger(__name__)


def detect_available_vram() -> Tuple[float, float]:
    """
    Detect available VRAM and RAM in GB.

    Returns:
        Tuple of (vram_gb, ram_gb). vram_gb is 0 if no GPU detected.
    """
    vram_gb = 0.0
    ram_gb = 0.0

    # 1. Detect VRAM using pynvml (NVIDIA)
    try:
        import pynvml

        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram_gb = info.free / (1024**3)
            logger.info("gpu_detected", device_count=device_count, vram_free_gb=vram_gb)
        pynvml.nvmlShutdown()
    except ImportError:
        logger.debug("pynvml_not_installed_skipping_gpu_check")
    except Exception as e:
        logger.warning("gpu_detection_failed", error=str(e))

    # 2. Detect System RAM
    try:
        import psutil

        vm = psutil.virtual_memory()
        ram_gb = vm.available / (1024**3)
    except ImportError:
        # Fallback if psutil not installed (though usually standard)
        # Use os.sysconf if on Unix
        try:
            if hasattr(os, "sysconf"):
                ram_gb = (
                    os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")
                ) / (1024**3)
        except Exception:
            logger.warning("ram_detection_failed")

    return vram_gb, ram_gb


def detect_optimal_quantization(model_size_params_b: float) -> str:
    """
    Suggest optimal quantization level based on available hardware.

    Args:
        model_size_params_b: Model parameter count in billions (e.g. 7.0 for 7B)

    Returns:
        Recommended quantization string (e.g. "Q4_K_M", "Q8_0")
    """
    vram_gb, ram_gb = detect_available_vram()
    total_mem_gb = vram_gb + ram_gb

    # Rough estimates of memory usage per quantization level (for 7B model)
    # Q4_K_M: ~4.5 GB
    # Q5_K_M: ~5.5 GB
    # Q8_0:   ~8.0 GB
    # FP16:   ~14.0 GB

    # Scaling factor based on parameter count (relative to 7B)
    scale = model_size_params_b / 7.0

    req_q4 = 4.5 * scale
    req_q5 = 5.5 * scale
    req_q8 = 8.0 * scale
    req_fp16 = 14.0 * scale

    # Buffer for system overhead (1-2 GB)
    overhead = 2.0
    available_for_model = total_mem_gb - overhead

    if available_for_model >= req_fp16:
        return "FP16"
    elif available_for_model >= req_q8:
        return "Q8_0"
    elif available_for_model >= req_q5:
        return "Q5_K_M"
    elif available_for_model >= req_q4:
        return "Q4_K_M"
    else:
        logger.warning(
            "insufficient_memory_for_model",
            model_size=model_size_params_b,
            available_gb=available_for_model,
            required_min_gb=req_q4,
        )
        return "Q4_K_M"  # Try smallest anyway


def estimate_gpu_layers(model_path: str, vram_gb: float) -> int:
    """
    Estimate how many layers can fit on GPU.

    Args:
        model_path: Path to GGUF model
        vram_gb: Available VRAM in GB

    Returns:
        Number of layers to offload (-1 for all, 0 for none, or specific count)
    """
    if vram_gb <= 0:
        return 0

    try:
        file_size_gb = os.path.getsize(model_path) / (1024**3)

        # Heuristic: If model fits entirely in VRAM with 1GB buffer, load all
        if vram_gb > (file_size_gb + 1.0):
            return -1

        # Otherwise, estimate layers (rough approximation)
        # Assuming typical transformer model ~32-40 layers
        # and linear distribution of size
        fraction = (vram_gb - 1.0) / file_size_gb
        if fraction <= 0:
            return 0

        estimated_layers = int(fraction * 32)
        return max(0, estimated_layers)

    except Exception as e:
        logger.error("gpu_layer_estimation_failed", error=str(e))
        return 0
