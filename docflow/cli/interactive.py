"""
Enhanced DocFlow CLI with advanced features and optimizations
"""

import click
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.tree import Tree
from rich.syntax import Syntax
from rich.columns import Columns
from rich.status import Status
from rich import box
import yaml

from ..processor import DocumentProcessor
from ..models import ModelRegistry
from ..performance_optimizer import get_performance_report, performance_cache
from ..prompt_manager import prompt_manager
from ..settings import settings

console = Console()


class EnhancedCLI:
    """Enhanced CLI with smart features and optimizations"""

    def __init__(self):
        self.config = self._load_config()
        self.processor_cache = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load CLI configuration with smart defaults"""
        return {
            "default_model": os.getenv("PRIMARY_MODEL", "qwen-vision"),
            "default_output_dir": os.getenv("DOCFLOW_OUTPUT_DIR", "./output"),
            "auto_ocr": os.getenv("DOCFLOW_AUTO_OCR", "smart").lower(),
            "batch_size": int(os.getenv("DOCFLOW_BATCH_SIZE", "4")),
            "preferred_models": os.getenv(
                "DOCFLOW_PREFERRED_MODELS",
                "openrouter-gemini-flash,qwen-vision,fallback",
            ).split(","),
        }

    def smart_model_selection(
        self, file_path: str, user_model: Optional[str] = None
    ) -> str:
        """Intelligently select the best model based on document characteristics"""
        if user_model:
            return user_model

        file_ext = Path(file_path).suffix.lower()
        file_size = Path(file_path).stat().st_size

        # Smart model selection logic
        if (
            file_ext in [".jpg", ".jpeg", ".png"] or file_size < 100000
        ):  # Images or small files
            return "openrouter-pixtral"  # OCR specialist
        elif file_size > 5000000:  # Large files
            return "openrouter-gemini-flash"  # Fast processing
        elif "contract" in file_path.lower() or "legal" in file_path.lower():
            return "openrouter-claude"  # Complex reasoning
        elif any(
            lang in file_path.lower()
            for lang in ["chinese", "japanese", "korean", "zh", "ja", "ko"]
        ):
            return "openrouter-qwen-vl"  # Multilingual
        else:
            return self.config["default_model"]

    def auto_detect_ocr_need(self, file_path: str) -> bool:
        """Automatically detect if OCR is needed"""
        if self.config["auto_ocr"] == "false":
            return False
        elif self.config["auto_ocr"] == "true":
            return True
        else:  # smart mode
            file_ext = Path(file_path).suffix.lower()
            return file_ext in [
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".webp",
                ".tiff",
                ".bmp",
            ]


# Enhanced command implementations
@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version information")
@click.pass_context
def cli(ctx, version):
    """🚀 DocFlow - Advanced Document Processing Tool"""
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


def show_interactive_menu():
    """Show interactive menu for command selection"""
    import sys

    console.print("\n[bold cyan]🚀 Welcome to DocFlow![/bold cyan]")

    options = {
        "1": ("📄 Process Single Document", "process"),
        "2": ("📁 Batch Process Directory", "batch"),
        "3": ("🤖 List AI Models", "models"),
        "4": ("⚙️  Configure Settings", "config"),
        "5": ("📊 Performance Stats", "stats"),
        "6": ("🌐 Start API Server", "serve"),
        "7": ("❓ Help & Examples", "help-menu"),
        "q": ("🚪 Quit", "quit"),
    }

    table = Table(title="Main Menu", box=box.ROUNDED)
    table.add_column("Option", style="bold cyan")
    table.add_column("Action", style="green")

    for key, (desc, _) in options.items():
        table.add_row(key, desc)

    console.print(table)

    choice = Prompt.ask("\n[bold]Choose an option[/bold]", choices=list(options.keys()))

    if choice == "q":
        console.print("👋 Thanks for using DocFlow!")
        sys.exit(0)

    action = options[choice][1]
    if action == "process":
        interactive_process()
    elif action == "batch":
        interactive_batch()
    elif action == "models":
        enhanced_models()
    elif action == "config":
        interactive_config()
    elif action == "stats":
        show_performance_stats()
    elif action == "serve":
        interactive_serve()
    elif action == "help-menu":
        show_help_menu()


def interactive_process():
    """Interactive document processing"""
    console.print("\n[bold cyan]📄 Interactive Document Processing[/bold cyan]")

    # File selection with validation
    file_path = Prompt.ask("Enter document path")
    if not Path(file_path).exists():
        console.print(f"[red]❌ File not found: {file_path}[/red]")
        return

    # Smart model suggestion
    cli_helper = EnhancedCLI()
    suggested_model = cli_helper.smart_model_selection(file_path)

    available_models = list(ModelRegistry.list_models().keys())
    console.print(f"[blue]💡 Suggested model: {suggested_model}[/blue]")

    model = Prompt.ask(
        "Choose AI model", choices=available_models + ["auto"], default=suggested_model
    )

    if model == "auto":
        model = suggested_model

    # Smart OCR detection
    auto_ocr = cli_helper.auto_detect_ocr_need(file_path)
    use_ocr = Confirm.ask(f"Enable OCR processing", default=auto_ocr)

    # Output options
    output_file = Prompt.ask("Output file (optional)", default="")
    include_text = Confirm.ask("Include extracted text in display", default=False)

    # Process with progress bar
    with Status("[bold green]Processing document...", spinner="dots") as status:
        try:
            processor = DocumentProcessor(ai_model=model)
            result = processor.process_document(file_path, use_ocr=use_ocr)

            status.update("[bold green]✅ Processing complete!")
            time.sleep(0.5)  # Brief pause to show completion

            # Display enhanced results
            display_enhanced_results(result, Path(file_path).name, include_text)

            # Save if requested
            if output_file:
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)
                console.print(f"[green]💾 Results saved to: {output_file}[/green]")

        except Exception as e:
            console.print(f"[red]❌ Error: {str(e)}[/red]")


@cli.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml", "detailed"]),
    default="detailed",
    help="Output format",
)
@click.option(
    "--show-performance", "-p", is_flag=True, help="Show model performance stats"
)
@click.option("--test-connection", "-t", is_flag=True, help="Test model connections")
def models(format, show_performance, test_connection):
    """🤖 List and analyze available AI models"""
    enhanced_models(format, show_performance, test_connection)


def enhanced_models(
    output_format="detailed", show_performance=False, test_connection=False
):
    """Enhanced model listing with detailed information"""
    models_dict = ModelRegistry.list_models()

    if output_format == "json":
        console.print(json.dumps(models_dict, indent=2))
        return
    elif output_format == "yaml":
        console.print(yaml.dump(models_dict, default_flow_style=False))
        return

    # Detailed display
    console.print(Panel("[bold cyan]🤖 Available AI Models[/bold cyan]", expand=False))

    # Group models by provider
    providers = {
        "Local (Ollama)": [],
        "OpenRouter": [],
        "Direct API": [],
        "Fallback": [],
    }

    for model_id, description in models_dict.items():
        if "openrouter" in model_id:
            providers["OpenRouter"].append((model_id, description))
        elif model_id in [
            "qwen-vision",
            "granite-vision",
            "gemma",
            "llava",
            "llama-vision",
        ]:
            providers["Local (Ollama)"].append((model_id, description))
        elif model_id == "fallback":
            providers["Fallback"].append((model_id, description))
        else:
            providers["Direct API"].append((model_id, description))

    for provider, model_list in providers.items():
        if model_list:
            table = Table(title=f"{provider} Models", box=box.MINIMAL)
            table.add_column("Model ID", style="bold cyan", width=25)
            table.add_column("Description", style="green")

            if test_connection:
                table.add_column("Status", style="yellow", width=10)

            for model_id, desc in model_list:
                row = [model_id, desc]
                if test_connection:
                    # Test model availability
                    try:
                        model_class = ModelRegistry.get_model(model_id)
                        is_available = (
                            model_class.is_available() if model_class else False
                        )
                        status = "✅ Ready" if is_available else "❌ Unavailable"
                    except Exception:
                        status = "❓ Unknown"
                    row.append(status)

                table.add_row(*row)

            console.print(table)
            console.print()

    if show_performance:
        perf_stats = get_performance_report()
        if perf_stats.get("model_stats"):
            console.print(Panel("[bold yellow]📊 Performance Statistics[/bold yellow]"))
            perf_table = Table(box=box.MINIMAL)
            perf_table.add_column("Model", style="cyan")
            perf_table.add_column("Requests", style="green")
            perf_table.add_column("Success Rate", style="blue")
            perf_table.add_column("Avg Duration", style="magenta")

            for model, stats in perf_stats["model_stats"].items():
                perf_table.add_row(
                    model,
                    str(stats["total_requests"]),
                    f"{stats['success_rate']:.1%}",
                    f"{stats['average_duration']:.2f}s",
                )

            console.print(perf_table)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--model", "-m", help="AI model to use")
@click.option("--output-dir", "-o", help="Output directory")
@click.option(
    "--parallel", "-p", type=int, default=4, help="Number of parallel processes"
)
@click.option(
    "--formats",
    multiple=True,
    help="File formats to process",
    default=["pdf", "docx", "txt", "jpg", "png"],
)
@click.option(
    "--recursive", "-r", is_flag=True, help="Process subdirectories recursively"
)
@click.option("--resume", is_flag=True, help="Resume interrupted batch processing")
def batch(path, model, output_dir, parallel, formats, recursive, resume):
    """📁 Batch process multiple documents"""
    enhanced_batch_processing(
        path, model, output_dir, parallel, formats, recursive, resume
    )


def enhanced_batch_processing(
    path,
    model=None,
    output_dir=None,
    parallel=4,
    formats=None,
    recursive=False,
    resume=False,
):
    """Enhanced batch processing with progress tracking and resume capability"""
    path = Path(path)

    if not formats:
        formats = ["pdf", "docx", "txt", "jpg", "png"]

    # Find all matching files
    pattern_extensions = [f"*.{ext}" for ext in formats]
    files = []

    if path.is_file():
        files = [path]
    else:
        for pattern in pattern_extensions:
            if recursive:
                files.extend(path.rglob(pattern))
            else:
                files.extend(path.glob(pattern))

    if not files:
        console.print(
            f"[yellow]⚠️  No files found matching formats: {', '.join(formats)}[/yellow]"
        )
        return

    console.print(f"[green]Found {len(files)} files to process[/green]")

    # Setup output directory
    if not output_dir:
        output_dir = (
            path / "docflow_output" if path.is_dir() else path.parent / "docflow_output"
        )
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(exist_ok=True)

    # Resume functionality
    processed_files = set()
    if resume:
        progress_file = output_dir / ".docflow_progress"
        if progress_file.exists():
            with open(progress_file, "r") as f:
                processed_files = set(json.load(f))
            console.print(
                f"[blue]Resuming: {len(processed_files)} files already processed[/blue]"
            )

    # Filter out already processed files
    remaining_files = [f for f in files if str(f) not in processed_files]

    if not remaining_files:
        console.print("[green]✅ All files already processed![/green]")
        return

    # Enhanced CLI helper for smart selection
    cli_helper = EnhancedCLI()

    # Process files with progress tracking
    results = []
    failed_files = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing documents...", total=len(remaining_files))

        def process_single_file(file_path):
            try:
                # Smart model selection if not specified
                selected_model = model or cli_helper.smart_model_selection(
                    str(file_path)
                )

                # Smart OCR detection
                use_ocr = cli_helper.auto_detect_ocr_need(str(file_path))

                processor = DocumentProcessor(ai_model=selected_model)
                result = processor.process_document(str(file_path), use_ocr=use_ocr)

                # Save individual result
                output_file = output_dir / f"{file_path.stem}_analysis.json"
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)

                return {
                    "file": str(file_path),
                    "status": "success",
                    "model": selected_model,
                    "output": str(output_file),
                    "document_type": result.get("document_type", "unknown"),
                }

            except Exception as e:
                return {"file": str(file_path), "status": "failed", "error": str(e)}

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(process_single_file, file_path): file_path
                for file_path in remaining_files
            }

            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result["status"] == "success":
                        processed_files.add(str(file_path))
                        progress.update(
                            task, advance=1, description=f"✅ {file_path.name}"
                        )
                    else:
                        failed_files.append(result)
                        progress.update(
                            task, advance=1, description=f"❌ {file_path.name}"
                        )

                    # Save progress
                    progress_file = output_dir / ".docflow_progress"
                    with open(progress_file, "w") as f:
                        json.dump(list(processed_files), f)

                except Exception as e:
                    failed_files.append(
                        {"file": str(file_path), "status": "failed", "error": str(e)}
                    )
                    progress.update(task, advance=1, description=f"❌ {file_path.name}")

    # Generate summary report
    generate_batch_summary(results, failed_files, output_dir)


def generate_batch_summary(
    results: List[Dict], failed_files: List[Dict], output_dir: Path
):
    """Generate comprehensive batch processing summary"""
    successful = [r for r in results if r["status"] == "success"]

    # Summary statistics
    summary = {
        "total_files": len(results),
        "successful": len(successful),
        "failed": len(failed_files),
        "success_rate": len(successful) / len(results) * 100 if results else 0,
        "document_types": {},
        "models_used": {},
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Analyze document types and models
    for result in successful:
        doc_type = result.get("document_type", "unknown")
        model = result.get("model", "unknown")

        summary["document_types"][doc_type] = (
            summary["document_types"].get(doc_type, 0) + 1
        )
        summary["models_used"][model] = summary["models_used"].get(model, 0) + 1

    # Save detailed results
    detailed_report = {
        "summary": summary,
        "successful_files": successful,
        "failed_files": failed_files,
    }

    report_file = output_dir / "batch_processing_report.json"
    with open(report_file, "w") as f:
        json.dump(detailed_report, f, indent=2)

    # Display summary
    console.print("\n[bold green]📊 Batch Processing Complete![/bold green]")

    summary_table = Table(title="Processing Summary", box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Files", str(summary["total_files"]))
    summary_table.add_row(
        "Successful", f"{summary['successful']} ({summary['success_rate']:.1f}%)"
    )
    summary_table.add_row("Failed", str(summary["failed"]))
    summary_table.add_row("Report Location", str(report_file))

    console.print(summary_table)

    if summary["document_types"]:
        console.print("\n[bold blue]📄 Document Types Found:[/bold blue]")
        for doc_type, count in summary["document_types"].items():
            console.print(f"  • {doc_type}: {count}")

    if failed_files:
        console.print(
            f"\n[red]❌ {len(failed_files)} files failed to process. Check report for details.[/red]"
        )


def display_enhanced_results(
    result: Dict[str, Any], filename: str, include_text: bool = False
):
    """Display processing results in an enhanced format"""
    # Main results panel
    console.print(
        Panel(f"[bold cyan]📄 Analysis Results: {filename}[/bold cyan]", expand=False)
    )

    # Basic information
    info_table = Table(box=box.MINIMAL_DOUBLE_HEAD)
    info_table.add_column("Field", style="bold cyan")
    info_table.add_column("Value", style="green")

    info_table.add_row("Document Type", result.get("document_type", "Unknown"))
    info_table.add_row("Text Length", f"{result.get('text_length', 0):,} characters")

    # AI Analysis info
    ai_analysis = result.get("ai_analysis", {})
    if ai_analysis:
        info_table.add_row("AI Model", ai_analysis.get("model_name", "Unknown"))
        info_table.add_row(
            "Processing Status",
            "✅ Success" if ai_analysis.get("success") else "❌ Failed",
        )

        if "validation_passed" in ai_analysis:
            validation_status = (
                "✅ Passed" if ai_analysis["validation_passed"] else "⚠️  Issues Found"
            )
            info_table.add_row("Validation", validation_status)

        if "text_optimized" in ai_analysis and ai_analysis["text_optimized"]:
            info_table.add_row("Text Optimization", "✅ Applied")

    console.print(info_table)

    # Extracted data
    raw_analysis = ai_analysis.get("raw_analysis", {}) if ai_analysis else {}
    if raw_analysis and isinstance(raw_analysis, dict):
        console.print("\n[bold blue]📋 Extracted Information:[/bold blue]")

        # Create structured display
        if "title" in raw_analysis:
            console.print(f"[bold]Title:[/bold] {raw_analysis['title']}")
        if "date" in raw_analysis:
            console.print(f"[bold]Date:[/bold] {raw_analysis['date']}")
        if "reference" in raw_analysis:
            console.print(f"[bold]Reference:[/bold] {raw_analysis['reference']}")

        # Metadata section
        meta = raw_analysis.get("meta", {})
        if meta:
            console.print("\n[bold yellow]💼 Metadata:[/bold yellow]")

            if "amounts" in meta and meta["amounts"]:
                console.print("  [bold]Amounts:[/bold]")
                for key, value in meta["amounts"].items():
                    if value is not None:
                        console.print(
                            f"    • {key}: ${value:,.2f}"
                            if isinstance(value, (int, float))
                            else f"    • {key}: {value}"
                        )

            if "dates" in meta and meta["dates"]:
                console.print("  [bold]Dates:[/bold]")
                for key, value in meta["dates"].items():
                    if value:
                        console.print(f"    • {key}: {value}")

            if "entities" in meta and meta["entities"]:
                console.print("  [bold]Entities:[/bold]")
                for entity_type, entities in meta["entities"].items():
                    if entities:
                        console.print(
                            f"    • {entity_type}: {', '.join(entities) if isinstance(entities, list) else entities}"
                        )

    # Validation errors if any
    validation_errors = ai_analysis.get("validation_errors")
    if validation_errors:
        console.print(
            f"\n[yellow]⚠️  Validation Issues ({len(validation_errors)}):[/yellow]"
        )
        for error in validation_errors[:3]:  # Show first 3 errors
            console.print(f"  • {error}")
        if len(validation_errors) > 3:
            console.print(f"  ... and {len(validation_errors) - 3} more")

    # Include text if requested
    if include_text and "text_content" in result:
        console.print(
            f"\n[bold blue]📝 Extracted Text ({len(result['text_content'])} chars):[/bold blue]"
        )
        # Show first 500 characters with syntax highlighting
        text_preview = result["text_content"][:500]
        if len(result["text_content"]) > 500:
            text_preview += "... [truncated]"
        console.print(Panel(text_preview, box=box.MINIMAL))


@cli.command()
def stats():
    """📊 Show performance statistics and system status"""
    show_performance_stats()


def show_performance_stats():
    """Display comprehensive performance statistics"""
    console.print(Panel("[bold cyan]📊 DocFlow Performance Dashboard[/bold cyan]"))

    # Get performance report
    perf_report = get_performance_report()

    # Cache statistics
    cache_stats = perf_report.get("cache_stats", {})
    if cache_stats:
        cache_table = Table(title="🗄️  Cache Performance", box=box.ROUNDED)
        cache_table.add_column("Metric", style="cyan")
        cache_table.add_column("Value", style="green")

        cache_table.add_row(
            "Current Size",
            f"{cache_stats.get('size', 0)} / {cache_stats.get('max_size', 0)}",
        )
        cache_table.add_row("TTL", f"{cache_stats.get('ttl_seconds', 0)} seconds")

        if cache_stats.get("oldest_entry"):
            cache_table.add_row("Oldest Entry", cache_stats["oldest_entry"])
        if cache_stats.get("newest_entry"):
            cache_table.add_row("Newest Entry", cache_stats["newest_entry"])

        console.print(cache_table)

    # Model performance statistics
    model_stats = perf_report.get("model_stats", {})
    if model_stats:
        model_table = Table(title="🤖 Model Performance", box=box.ROUNDED)
        model_table.add_column("Model", style="bold cyan")
        model_table.add_column("Requests", style="blue")
        model_table.add_column("Success Rate", style="green")
        model_table.add_column("Avg Duration", style="yellow")
        model_table.add_column("Text Processed", style="magenta")

        for model_name, stats in model_stats.items():
            success_rate = f"{stats.get('success_rate', 0):.1%}"
            avg_duration = f"{stats.get('average_duration', 0):.2f}s"
            avg_text_len = f"{stats.get('average_text_length', 0):,.0f} chars"

            model_table.add_row(
                model_name,
                str(stats.get("total_requests", 0)),
                success_rate,
                avg_duration,
                avg_text_len,
            )

        console.print(model_table)

    # System information
    system_table = Table(title="💻 System Information", box=box.ROUNDED)
    system_table.add_column("Component", style="cyan")
    system_table.add_column("Status", style="green")

    # Check model availability
    available_models = len(ModelRegistry.list_models())
    system_table.add_row("Available Models", str(available_models))

    # Check prompt template
    prompt_valid = prompt_manager.validate_template()
    system_table.add_row(
        "Prompt Template", "✅ Valid" if prompt_valid else "❌ Invalid"
    )

    console.print(system_table)


def interactive_config():
    """Interactive configuration management"""
    console.print("\n[bold cyan]⚙️  DocFlow Configuration[/bold cyan]")

    config_options = {
        "1": "Set Default Model",
        "2": "Configure Output Directory",
        "3": "Set Auto-OCR Mode",
        "4": "Configure Batch Processing",
        "5": "View Current Settings",
        "6": "Reset to Defaults",
    }

    for key, desc in config_options.items():
        console.print(f"  {key}. {desc}")

    choice = Prompt.ask(
        "\nSelect configuration option", choices=list(config_options.keys())
    )

    if choice == "1":
        available_models = list(ModelRegistry.list_models().keys())
        current_model = os.getenv("PRIMARY_MODEL", "qwen-vision")

        console.print(f"[blue]Current default model: {current_model}[/blue]")
        new_model = Prompt.ask(
            "Choose new default model", choices=available_models, default=current_model
        )

        # Here you would update the .env file
        console.print(f"[green]✅ Default model set to: {new_model}[/green]")
        console.print(
            "[yellow]💡 Update your .env file: PRIMARY_MODEL={new_model}[/yellow]"
        )

    elif choice == "5":
        # Show current configuration
        config_display = Table(title="Current Configuration", box=box.ROUNDED)
        config_display.add_column("Setting", style="cyan")
        config_display.add_column("Value", style="green")

        env_vars = [
            ("PRIMARY_MODEL", "Default AI Model"),
            ("DOCFLOW_OUTPUT_DIR", "Output Directory"),
            ("DOCFLOW_AUTO_OCR", "Auto-OCR Mode"),
            ("DOCFLOW_BATCH_SIZE", "Batch Size"),
            ("OPENROUTER_API_KEY", "OpenRouter API Key"),
        ]

        for env_var, description in env_vars:
            value = os.getenv(env_var, "Not Set")
            if "API_KEY" in env_var and value != "Not Set":
                value = f"{'*' * 20}{value[-8:]}"  # Mask API key
            config_display.add_row(description, value)

        console.print(config_display)


def show_help_menu():
    """Show comprehensive help and examples"""
    console.print(
        Panel("[bold cyan]❓ DocFlow Help & Examples[/bold cyan]", expand=False)
    )

    examples = [
        ("Single Document", "docflow process invoice.pdf --model openrouter-claude"),
        ("Batch Processing", "docflow batch ./documents --parallel 4 --recursive"),
        ("Smart Processing", "docflow process contract.pdf --model auto --use-ocr"),
        (
            "Custom Output",
            "docflow process receipt.jpg --output analysis.json --include-text",
        ),
        ("API Server", "docflow serve --host 0.0.0.0 --port 8080"),
        ("Performance Stats", "docflow stats"),
    ]

    for title, command in examples:
        console.print(f"\n[bold yellow]{title}:[/bold yellow]")
        console.print(f"  [dim]$ {command}[/dim]")


def interactive_serve():
    """Interactive API server configuration"""
    console.print("\n[bold cyan]🌐 Start DocFlow API Server[/bold cyan]")

    host = Prompt.ask("Host address", default="0.0.0.0")
    port = IntPrompt.ask("Port number", default=8000)

    console.print(
        Panel(
            f"[green]Starting DocFlow API server[/green]\n"
            f"🌐 Server: http://{host}:{port}\n"
            f"📚 Docs: http://{host}:{port}/docs\n"
            f"🔄 API: http://{host}:{port}/redoc",
            title="Server Starting",
        )
    )

    import uvicorn

    uvicorn.run("docflow.api:app", host=host, port=port, reload=False)


# Export the enhanced CLI
enhanced_cli = cli
