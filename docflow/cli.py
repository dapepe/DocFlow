"""DocFlow CLI module for command line interface functionality"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import uvicorn
from .processor import DocumentProcessor
import logging
import os
from .models import ModelRegistry

# Import enhanced CLI features
from .enhanced_cli import enhanced_cli, show_interactive_menu
from .cli_workflows import workflow, smart_route, insights
from .cli_help import help as help_cmd

console = Console()
logger = logging.getLogger(__name__)

def get_available_models():
    """Get list of available model IDs"""
    try:
        models = ModelRegistry.list_models()
        if not models:
            logger.warning("No models available, using fallback")
            return ['fallback']
        return list(models.keys())
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return ['fallback']

def set_verbose_logging(verbose: bool):
    """Configure logging based on verbosity"""
    # Set environment variable for logging configuration
    os.environ['DOCFLOW_LOG_LEVEL'] = 'DEBUG' if verbose else 'ERROR'
    # Re-initialize logging
    from .config import setup_logging
    setup_logging()

def verbose_option(f):
    """Decorator to add verbose option to commands"""
    def callback(ctx, param, value):
        if value:
            set_verbose_logging(True)
        return value
    return click.option('--verbose', is_flag=True, 
                       help="Enable verbose logging",
                       callback=callback)(f)

@click.group(invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help="Show version information")
@verbose_option
@click.pass_context
def cli(ctx, version, verbose):
    """🚀 DocFlow - Advanced AI-Powered Document Processing Tool"""
    if version:
        console.print(Panel(
            "[bold blue]DocFlow v2.0[/bold blue]\n"
            "Advanced AI-Powered Document Processing\n"
            "🎯 15+ AI Models | 🔥 Smart Processing | ⚡ Enterprise Ready",
            title="Version Info"
        ))
        return
    
    if ctx.invoked_subcommand is None:
        show_interactive_menu()

@cli.command()
@verbose_option
def models(verbose):
    """List available AI models"""
    processor = DocumentProcessor()
    models = processor.get_supported_models()

    table = Table(title="Available AI Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Description", style="green")

    for model_id, description in models.items():
        table.add_row(model_id, description)

    console.print(table)

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--use-ocr', is_flag=True, help="Enable OCR processing")
@click.option('--output', '-o', type=click.Path(), help="Output file path for JSON results")
@click.option('--model', '-m', 
              type=click.Choice(get_available_models(), case_sensitive=False),
              default=lambda: os.getenv('PRIMARY_MODEL', 'qwen-vision'),  # Default from environment or qwen-vision
              help="Choose AI model for document analysis. Available: qwen-vision (Qwen2.5VL), granite-vision (Granite3.2), gemma (Gemma3), llava (LLaVA), llama-vision (Llama3.2), mistral-document (Mistral+OCR), gpt4-vision (OpenAI), openrouter-claude (Claude via OpenRouter), openrouter-gpt4-vision (GPT-4V via OpenRouter), openrouter-gemini-flash (Gemini Flash via OpenRouter), openrouter-gemini-pro (Gemini Pro via OpenRouter), openrouter-qwen-vl (Qwen-VL via OpenRouter), openrouter-pixtral (Pixtral via OpenRouter), openrouter-llava (LLaVA via OpenRouter), fallback (basic)")
@click.option('--include-text', is_flag=True, help="Display the extracted text content")
@click.option('--save-text', type=click.Path(), help="Save extracted text to a separate file")
@verbose_option
def process(file_path: str, use_ocr: bool, output: str, model: str, include_text: bool, save_text: str, verbose: bool):
    """Process a single document with optional AI model selection"""
    try:
        processor = DocumentProcessor(ai_model=model)
        result = processor.process_document(file_path, use_ocr=use_ocr)

        # Create result table
        table = Table(title=f"Processing Results: {Path(file_path).name}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        # Add basic fields
        table.add_row("Document Type", result['document_type'])
        table.add_row("Text Length", str(result['text_length']))

        # Add metadata rows
        for key, value in result.get('metadata', {}).items():
            table.add_row(key, str(value))

        # Add AI analysis summary if available
        ai_analysis = result.get('ai_analysis', {})
        if ai_analysis and ai_analysis.get('success'):
            table.add_row("AI Model", ai_analysis.get('model_name', 'Unknown'))
            raw_analysis = ai_analysis.get('raw_analysis', '')
            if isinstance(raw_analysis, dict):
                for key, value in raw_analysis.items():
                    table.add_row(f"AI {key}", str(value))
            else:
                # Truncate long analysis text for display
                analysis_preview = str(raw_analysis)[:200] + "..." if len(str(raw_analysis)) > 200 else str(raw_analysis)
                table.add_row("AI Analysis", analysis_preview)

        console.print(table)

        # Handle text content display/save options
        if include_text and 'text_content' in result:
            console.print("\nExtracted Text Content:", style="blue")
            console.print(result['text_content'])

        if save_text and 'text_content' in result:
            with open(save_text, 'w', encoding='utf-8') as f:
                f.write(result['text_content'])
            console.print(f"\nText content saved to: {save_text}", style="blue")

        # Remove text_content from JSON output if not requested
        if not include_text and not save_text and 'text_content' in result:
            del result['text_content']

        # Save results to JSON if output path provided
        if output:
            import json
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            console.print(f"Results saved to: {output}", style="blue")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"CLI processing error: {e}", exc_info=True)

@cli.command()
@click.option('--host', default='0.0.0.0', help="Host to bind to")
@click.option('--port', default=8000, help="Port to bind to")
@verbose_option
def serve(host: str, port: int, verbose: bool):
    """Start the REST API server"""
    try:
        console.print(Panel.fit(
            "[green]Starting DocFlow API server[/green]\n"
            f"API documentation will be available at http://{host}:{port}/docs",
            title="DocFlow Server"
        ))
        uvicorn.run("docflow.api:app", host=host, port=port, reload=False)
    except Exception as e:
        console.print(f"[red]Error starting server:[/red] {str(e)}")
        logger.error(f"Server startup error: {e}")

# Add advanced workflow commands
cli.add_command(workflow)
cli.add_command(smart_route)
cli.add_command(insights)
cli.add_command(help_cmd)