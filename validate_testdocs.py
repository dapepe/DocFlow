#!/usr/bin/env python3
"""
Validation script for test documents.
Extracts information from test PDFs and validates against schema.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PyPDF2 import PdfReader
    from jsonschema import validate, ValidationError
except ImportError as e:
    console.print(f"[red]Missing dependency: {e}[/red]")
    console.print("[yellow]Please install: PyPDF2 jsonschema rich[/yellow]")
    sys.exit(1)

# Load schema
SCHEMA_PATH = Path(__file__).parent / "config" / "schema.json"
TESTDOCS_DIR = Path(__file__).parent / "testdocs"
OUTPUT_DIR = TESTDOCS_DIR / "out"


def load_schema():
    """Load JSON schema."""
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)


def extract_basic_info(pdf_path):
    """Extract basic information from PDF."""
    reader = PdfReader(pdf_path)
    info = {
        "file_name": pdf_path.name,
        "page_count": len(reader.pages),
        "text_preview": "",
        "metadata": {},
    }

    # Get metadata
    if reader.metadata:
        info["metadata"] = {
            "title": reader.metadata.get("/Title", ""),
            "author": reader.metadata.get("/Author", ""),
            "creator": reader.metadata.get("/Creator", ""),
            "producer": reader.metadata.get("/Producer", ""),
        }

    # Extract text from first page
    if len(reader.pages) > 0:
        try:
            first_page = reader.pages[0]
            text = first_page.extract_text()
            info["text_preview"] = text[:500] if text else ""
        except Exception as e:
            info["text_preview"] = f"Error extracting text: {e}"

    return info


def generate_mock_result(pdf_info):
    """Generate a mock result that matches the schema structure."""
    # This is a simplified mock - in real usage, AI would process this
    return {
        "date": "2025-01-15",  # Default date for testing
        "title": pdf_info["metadata"].get("title") or pdf_info["file_name"],
        "doctype": "other",
        "reference": None,
        "meta": {
            "dates": {},
            "amounts": {},
            "entities": {"organizations": [], "people": []},
        },
    }


def validate_result(result, schema):
    """Validate result against schema."""
    try:
        validate(instance=result, schema=schema)
        return True, "Valid"
    except ValidationError as e:
        return False, str(e)


def save_result(pdf_path, result):
    """Save result to JSON file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"{pdf_path.stem}_result.json"

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    return output_path


def main():
    """Main validation function."""
    console.print(Panel.fit("[bold cyan]DocFlow Test Document Validation[/bold cyan]"))

    # Load schema
    console.print("\n[blue]📋 Loading schema...[/blue]")
    schema = load_schema()
    console.print("[green]✓ Schema loaded[/green]")

    # Find test PDFs
    pdf_files = list(TESTDOCS_DIR.glob("*.pdf"))
    console.print(f"\n[bold]📄 Found {len(pdf_files)} test PDFs[/bold]")

    # Process each PDF
    results = []
    for pdf_path in sorted(pdf_files):
        console.print(f"\n[bold cyan]Processing: {pdf_path.name}[/bold cyan]")

        # Extract basic info
        console.print("  Extracting basic info...")
        pdf_info = extract_basic_info(pdf_path)
        console.print(f"    - Pages: [blue]{pdf_info['page_count']}[/blue]")
        console.print(
            f"    - Title: [blue]{pdf_info['metadata'].get('title', 'N/A')}[/blue]"
        )
        console.print(
            f"    - Author: [blue]{pdf_info['metadata'].get('author', 'N/A')}[/blue]"
        )

        # Generate mock result (in real usage, would use AI)
        console.print("  Generating result structure...")
        result = generate_mock_result(pdf_info)

        # Validate against schema
        console.print("  Validating against schema...")
        is_valid, validation_message = validate_result(result, schema)

        if is_valid:
            console.print("  [green]✓ Result is valid[/green]")
            # Save result
            output_path = save_result(pdf_path, result)
            console.print(f"  [green]✓ Saved to: {output_path}[/green]")
        else:
            console.print(f"  [red]✗ Validation failed: {validation_message}[/red]")

        results.append(
            {
                "file": pdf_path.name,
                "valid": is_valid,
                "error": validation_message if not is_valid else None,
                "pages": pdf_info["page_count"],
            }
        )

    # Summary
    console.print("\n[bold]Validation Summary[/bold]")

    valid_count = sum(1 for r in results if r["valid"])
    total_count = len(results)

    summary_table = Table(box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Files", str(total_count))
    summary_table.add_row("Valid", str(valid_count))
    summary_table.add_row(
        "Invalid",
        f"[red]{total_count - valid_count}[/red]"
        if total_count - valid_count > 0
        else "0",
    )

    console.print(summary_table)

    console.print("\n[bold]Details:[/bold]")
    results_table = Table(box=box.MINIMAL)
    results_table.add_column("Status", justify="center")
    results_table.add_column("File")
    results_table.add_column("Pages", justify="right")
    results_table.add_column("Error", style="red")

    for r in results:
        status = "[green]✓[/green]" if r["valid"] else "[red]✗[/red]"
        error = r["error"] if not r["valid"] else ""
        results_table.add_row(status, r["file"], str(r["pages"]), error)

    console.print(results_table)

    # Exit with appropriate code
    sys.exit(0 if all(r["valid"] for r in results) else 1)


if __name__ == "__main__":
    main()
