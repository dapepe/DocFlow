"""DocFlow CLI module for command line interface functionality"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import uvicorn
from .processor import DocumentProcessor
import structlog
import os
import json
import time
from .models import ModelRegistry
from ..performance_optimizer import get_performance_report

# Import enhanced CLI features
from .enhanced_cli import enhanced_cli, show_interactive_menu
from .cli_workflows import workflow, smart_route, insights
from .cli_help import help as help_cmd

console = Console()
logger = structlog.get_logger(__name__)


def get_available_models():
    """Get list of available model IDs"""
    try:
        models = ModelRegistry.list_models()
        if not models:
            logger.warning("No models available, using fallback")
            return ["fallback"]
        return list(models.keys())
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return ["fallback"]


def set_verbose_logging(verbose: bool):
    """Configure logging based on verbosity"""
    # Set environment variable for logging configuration
    os.environ["DOCFLOW_LOG_LEVEL"] = "DEBUG" if verbose else "ERROR"
    # Re-initialize logging
    from .config import setup_logging

    setup_logging()


def verbose_option(f):
    """Decorator to add verbose option to commands"""

    def callback(ctx, param, value):
        if value:
            set_verbose_logging(True)
        return value

    return click.option(
        "--verbose", is_flag=True, help="Enable verbose logging", callback=callback
    )(f)


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version information")
@verbose_option
@click.pass_context
def cli(ctx, version, verbose):
    """🚀 DocFlow - Advanced AI-Powered Document Processing Tool"""
    if version:
        console.print(
            Panel(
                "[bold blue]DocFlow v2.0[/bold blue]\n"
                "Advanced AI-Powered Document Processing\n"
                "🎯 15+ AI Models | 🔥 Smart Processing | ⚡ Enterprise Ready",
                title="Version Info",
            )
        )
        return

    if ctx.invoked_subcommand is None:
        show_interactive_menu()


@cli.command()
@verbose_option
def models(verbose):
    """List available AI models"""
    processor = DocumentProcessor()
    # Need to access registry directly to get model instances for capabilities
    models = ModelRegistry.list_models()

    table = Table(title="Available AI Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Capabilities", style="yellow")

    for model_id, description in models.items():
        capabilities = []
        try:
            model_class = ModelRegistry.get_model(model_id)
            if model_class:
                # Instantiate to get capabilities (might be heavy if model loads on init, but we designed lazy loading)
                # Actually, capabilities should be checkable without full load if possible,
                # but our design instantiates in __init__.
                # However, LocalProvider lazy loads in _ensure_model_loaded.
                # HTTPProvider is light.
                # So safe to instantiate.
                model_instance = model_class()
                caps = model_instance.get_capabilities()
                if caps.get("vision"):
                    capabilities.append("Vision")
                if caps.get("ocr"):
                    capabilities.append("OCR")
                if caps.get("local"):
                    capabilities.append("Local")
                if caps.get("fast"):
                    capabilities.append("Fast")
                if caps.get("gpu_acceleration"):
                    capabilities.append("GPU")
        except Exception:
            pass

        table.add_row(model_id, description, ", ".join(capabilities))

    console.print(table)


@cli.command()
@click.option(
    "--document", type=click.Path(exists=True), required=True, help="Test document path"
)
@click.option(
    "--models", "-m", multiple=True, help="Models to benchmark (default: all available)"
)
@click.option("--iterations", "-n", default=1, help="Number of iterations per model")
@verbose_option
def benchmark(document, models, iterations, verbose):
    """Benchmark model performance"""
    console.print(
        Panel(f"Benchmarking with document: {document}", title="Performance Benchmark")
    )

    available = ModelRegistry.list_models()
    target_models = models if models else list(available.keys())

    # Filter out fallback if not explicitly requested
    if not models and "fallback" in target_models:
        target_models.remove("fallback")

    results = []

    with console.status("[bold green]Running benchmark..."):
        for model_id in target_models:
            if model_id not in available:
                console.print(f"[yellow]Skipping unknown model: {model_id}[/yellow]")
                continue

            console.print(f"Testing {model_id}...", style="blue")
            durations = []
            success_count = 0

            try:
                processor = DocumentProcessor(ai_model=model_id)

                for i in range(iterations):
                    start = time.time()
                    # Force OCR for fair comparison if models support it
                    res = processor.process_document(document, use_ocr=False)
                    duration = time.time() - start

                    if res.get("ai_analysis", {}).get("success"):
                        success_count += 1
                        durations.append(duration)

            except Exception as e:
                logger.error("benchmark_error", model=model_id, error=str(e))

            if durations:
                avg_time = sum(durations) / len(durations)
                results.append(
                    {
                        "model": model_id,
                        "avg_time": avg_time,
                        "success_rate": f"{success_count}/{iterations}",
                        "min_time": min(durations),
                        "max_time": max(durations),
                    }
                )
            else:
                results.append(
                    {
                        "model": model_id,
                        "avg_time": float("inf"),
                        "success_rate": "0/0",
                        "min_time": 0,
                        "max_time": 0,
                    }
                )

    # Display results
    table = Table(title="Benchmark Results")
    table.add_column("Model", style="cyan")
    table.add_column("Avg Time (s)", style="green")
    table.add_column("Min/Max (s)", style="blue")
    table.add_column("Success Rate", style="yellow")

    # Sort by speed
    results.sort(key=lambda x: x["avg_time"])

    for r in results:
        avg = f"{r['avg_time']:.2f}" if r["avg_time"] != float("inf") else "N/A"
        min_max = f"{r['min_time']:.2f} / {r['max_time']:.2f}"
        table.add_row(r["model"], avg, min_max, r["success_rate"])

    console.print(table)


@cli.command()
def config():
    """Validate and display configuration"""
    from ..settings import settings

    table = Table(title="Current Configuration")
    table.add_column("Category", style="cyan")
    table.add_column("Setting", style="blue")
    table.add_column("Value", style="green")

    # API Settings
    table.add_row("API", "Host", settings.host)
    table.add_row("API", "Port", str(settings.port))

    # Model Settings
    table.add_row("Models", "Primary Model", settings.primary_model)
    table.add_row("Models", "Ollama Host", settings.ollama_host)

    # Provider Keys (masked)
    for provider in ["OPENAI", "ANTHROPIC", "GOOGLE", "MISTRAL", "OPENROUTER"]:
        key = getattr(settings, f"{provider.lower()}_api_key", None)
        status = "✅ Configured" if key else "❌ Missing"
        table.add_row("Providers", f"{provider} API Key", status)

    # Cache Stats
    stats = get_performance_report()
    cache_stats = stats["cache_stats"]
    table.add_row("Cache", "Entries", str(cache_stats.get("size", 0)))
    table.add_row("Cache", "Max Size", str(cache_stats.get("max_size", 0)))

    console.print(table)

    # Validation check
    from ..models.providers.quantization import detect_available_vram

    vram, ram = detect_available_vram()

    console.print("\n[bold]Hardware Detection:[/bold]")
    console.print(f"VRAM: {vram:.2f} GB")
    console.print(f"RAM:  {ram:.2f} GB")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--use-ocr", is_flag=True, help="Enable OCR processing")
@click.option(
    "--output", "-o", type=click.Path(), help="Output file path for JSON results"
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(get_available_models(), case_sensitive=False),
    default=lambda: os.getenv(
        "PRIMARY_MODEL", "qwen-vision"
    ),  # Default from environment or qwen-vision
    help="Choose AI model for document analysis. Available: qwen-vision (Qwen2.5VL), granite-vision (Granite3.2), gemma (Gemma3), llava (LLaVA), llama-vision (Llama3.2), mistral-document (Mistral+OCR), gpt4-vision (OpenAI), openrouter-claude (Claude via OpenRouter), openrouter-gpt4-vision (GPT-4V via OpenRouter), openrouter-gemini-flash (Gemini Flash via OpenRouter), openrouter-gemini-pro (Gemini Pro via OpenRouter), openrouter-qwen-vl (Qwen-VL via OpenRouter), openrouter-pixtral (Pixtral via OpenRouter), openrouter-llava (LLaVA via OpenRouter), fallback (basic)",
)
@click.option("--include-text", is_flag=True, help="Display the extracted text content")
@click.option(
    "--save-text", type=click.Path(), help="Save extracted text to a separate file"
)
@verbose_option
def process(
    file_path: str,
    use_ocr: bool,
    output: str,
    model: str,
    include_text: bool,
    save_text: str,
    verbose: bool,
):
    """Process a single document with optional AI model selection"""
    try:
        processor = DocumentProcessor(ai_model=model)
        result = processor.process_document(file_path, use_ocr=use_ocr)

        # Create result table
        table = Table(title=f"Processing Results: {Path(file_path).name}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        # Add basic fields
        table.add_row("Document Type", result["document_type"])
        table.add_row("Text Length", str(result["text_length"]))

        # Add metadata rows
        for key, value in result.get("metadata", {}).items():
            table.add_row(key, str(value))

        # Add AI analysis summary if available
        ai_analysis = result.get("ai_analysis", {})
        if ai_analysis and ai_analysis.get("success"):
            table.add_row("AI Model", ai_analysis.get("model_name", "Unknown"))
            raw_analysis = ai_analysis.get("raw_analysis", "")
            if isinstance(raw_analysis, dict):
                for key, value in raw_analysis.items():
                    table.add_row(f"AI {key}", str(value))
            else:
                # Truncate long analysis text for display
                analysis_preview = (
                    str(raw_analysis)[:200] + "..."
                    if len(str(raw_analysis)) > 200
                    else str(raw_analysis)
                )
                table.add_row("AI Analysis", analysis_preview)

        console.print(table)

        # Handle text content display/save options
        if include_text and "text_content" in result:
            console.print("\nExtracted Text Content:", style="blue")
            console.print(result["text_content"])

        if save_text and "text_content" in result:
            with open(save_text, "w", encoding="utf-8") as f:
                f.write(result["text_content"])
            console.print(f"\nText content saved to: {save_text}", style="blue")

        # Remove text_content from JSON output if not requested
        if not include_text and not save_text and "text_content" in result:
            del result["text_content"]

        # Save results to JSON if output path provided
        if output:
            import json

            with open(output, "w") as f:
                json.dump(result, f, indent=2)
            console.print(f"Results saved to: {output}", style="blue")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"CLI processing error: {e}", exc_info=True)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@verbose_option
def serve(host: str, port: int, verbose: bool):
    """Start the REST API server"""
    try:
        console.print(
            Panel.fit(
                "[green]Starting DocFlow API server[/green]\n"
                f"API documentation will be available at http://{host}:{port}/docs",
                title="DocFlow Server",
            )
        )
        uvicorn.run("docflow.api:app", host=host, port=port, reload=False)
    except Exception as e:
        console.print(f"[red]Error starting server:[/red] {str(e)}")
        logger.error(f"Server startup error: {e}")


# Add advanced workflow commands
cli.add_command(workflow)
cli.add_command(smart_route)
cli.add_command(insights)
cli.add_command(help_cmd)
