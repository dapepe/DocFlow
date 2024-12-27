import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import uvicorn
from .processor import DocumentProcessor
import logging

console = Console()
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """DocFlow - Document Processing Tool"""
    pass

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--use-ocr', is_flag=True, help="Enable OCR processing")
@click.option('--output', '-o', type=click.Path(), help="Output file path for JSON results")
@click.option('--model', '-m', 
              type=click.Choice(['gpt4-vision', 'gemini', 'llama-vision']), 
              help="Choose AI model for analysis")
@click.option('--include-text', is_flag=True, help="Display the extracted text content")
@click.option('--save-text', type=click.Path(), help="Save extracted text to a separate file")
def process(file_path: str, use_ocr: bool, output: str, model: str, include_text: bool, save_text: str):
    """Process a single document"""
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
        if include_text:
            console.print("\nExtracted Text Content:", style="blue")
            console.print(result['text_content'])

        if save_text:
            with open(save_text, 'w', encoding='utf-8') as f:
                f.write(result['text_content'])
            console.print(f"\nText content saved to: {save_text}", style="blue")

        # Remove text_content from JSON output if not requested
        if not include_text and not save_text and 'text_content' in result:
            del result['text_content']

        if output:
            import json
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            console.print(f"Results saved to: {output}", style="blue")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"CLI processing error: {e}")

@cli.command()
@click.option('--host', default='0.0.0.0', help="Host to bind to")
@click.option('--port', default=8000, help="Port to bind to")
def serve(host: str, port: int):
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