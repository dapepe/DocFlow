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
@click.option('--ocr', is_flag=True, help="Enable OCR processing")
@click.option('--output', '-o', type=click.Path(), help="Output file path for JSON results")
def process(file_path: str, ocr: bool, output: str):
    """Process a single document"""
    try:
        processor = DocumentProcessor()
        result = processor.process_document(file_path, use_ocr=ocr)

        # Create result table
        table = Table(title=f"Processing Results: {Path(file_path).name}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Document Type", result['document_type'])
        table.add_row("Text Length", str(result['text_length']))
        
        # Add metadata rows
        for key, value in result['metadata'].items():
            table.add_row(key, str(value))

        console.print(table)

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
