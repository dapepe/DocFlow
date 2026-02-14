"""
Advanced CLI Workflows and Automation
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich import box
import click

from ..processor import DocumentProcessor
from ..models import ModelRegistry

console = Console()


class DocumentWorkflow:
    """Advanced document processing workflows"""

    def __init__(self):
        self.workflows_dir = Path(".docflow/workflows")
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

    def create_workflow(self, name: str, config: Dict[str, Any]):
        """Create a new processing workflow"""
        workflow_file = self.workflows_dir / f"{name}.yaml"
        with open(workflow_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        console.print(f"[green]✅ Workflow '{name}' created at {workflow_file}[/green]")

    def list_workflows(self) -> List[str]:
        """List available workflows"""
        return [f.stem for f in self.workflows_dir.glob("*.yaml")]

    def run_workflow(self, name: str, input_path: str) -> Dict[str, Any]:
        """Execute a workflow"""
        workflow_file = self.workflows_dir / f"{name}.yaml"

        if not workflow_file.exists():
            raise ValueError(f"Workflow '{name}' not found")

        with open(workflow_file, "r") as f:
            config = yaml.safe_load(f)

        return self._execute_workflow_steps(config, input_path)

    def _execute_workflow_steps(
        self, config: Dict[str, Any], input_path: str
    ) -> Dict[str, Any]:
        """Execute workflow steps in sequence"""
        results = {"workflow_results": [], "final_output": None}

        for i, step in enumerate(config.get("steps", [])):
            console.print(
                f"[blue]Step {i + 1}: {step.get('name', 'Unnamed step')}[/blue]"
            )

            step_result = self._execute_step(step, input_path, results)
            results["workflow_results"].append(step_result)

            # Update input for next step if needed
            if step.get("pass_output_to_next", False):
                input_path = step_result.get("output_file", input_path)

        results["final_output"] = (
            results["workflow_results"][-1] if results["workflow_results"] else None
        )
        return results

    def _execute_step(
        self, step: Dict[str, Any], input_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step"""
        step_type = step.get("type")

        if step_type == "process":
            return self._execute_process_step(step, input_path)
        elif step_type == "validate":
            return self._execute_validation_step(step, context)
        elif step_type == "transform":
            return self._execute_transform_step(step, input_path)
        elif step_type == "export":
            return self._execute_export_step(step, context)
        else:
            raise ValueError(f"Unknown step type: {step_type}")


class SmartDocumentRouter:
    """Intelligent document routing based on content analysis"""

    def __init__(self):
        self.routing_rules = self._load_routing_rules()

    def _load_routing_rules(self) -> Dict[str, Any]:
        """Load document routing rules"""
        rules_file = Path(".docflow/routing_rules.yaml")

        if not rules_file.exists():
            # Create default rules
            default_rules = {
                "routes": {
                    "invoices": {
                        "keywords": ["invoice", "bill", "payment due", "amount due"],
                        "model": "openrouter-claude",
                        "ocr": "auto",
                        "output_dir": "./processed/invoices",
                        "required_fields": ["invoice_number", "total_amount", "date"],
                    },
                    "contracts": {
                        "keywords": ["contract", "agreement", "terms", "conditions"],
                        "model": "openrouter-claude",
                        "ocr": False,
                        "output_dir": "./processed/contracts",
                        "required_fields": ["parties", "effective_date", "terms"],
                    },
                    "receipts": {
                        "keywords": ["receipt", "purchase", "transaction"],
                        "model": "openrouter-gemini-flash",
                        "ocr": True,
                        "output_dir": "./processed/receipts",
                        "required_fields": ["merchant", "amount", "date"],
                    },
                    "forms": {
                        "file_extensions": [".jpg", ".jpeg", ".png"],
                        "model": "openrouter-pixtral",
                        "ocr": True,
                        "output_dir": "./processed/forms",
                        "required_fields": ["form_type"],
                    },
                }
            }

            rules_file.parent.mkdir(parents=True, exist_ok=True)
            with open(rules_file, "w") as f:
                yaml.dump(default_rules, f, default_flow_style=False)

        with open(rules_file, "r") as f:
            return yaml.safe_load(f)

    def route_document(
        self, file_path: str, preview_text: str = None
    ) -> Dict[str, Any]:
        """Determine the best processing route for a document"""
        file_path = Path(file_path)

        # Get preview text if not provided
        if not preview_text:
            preview_text = self._extract_preview_text(file_path)

        best_route = None
        best_score = 0

        for route_name, route_config in self.routing_rules["routes"].items():
            score = self._calculate_route_score(file_path, preview_text, route_config)

            if score > best_score:
                best_score = score
                best_route = {
                    "name": route_name,
                    "config": route_config,
                    "confidence": score,
                }

        return best_route or {
            "name": "default",
            "config": {
                "model": "qwen-vision",
                "ocr": "auto",
                "output_dir": "./processed/default",
            },
            "confidence": 0.1,
        }

    def _calculate_route_score(
        self, file_path: Path, preview_text: str, route_config: Dict
    ) -> float:
        """Calculate routing confidence score"""
        score = 0.0

        # Check file extension match
        if "file_extensions" in route_config:
            if file_path.suffix.lower() in route_config["file_extensions"]:
                score += 0.5

        # Check keyword matches
        if "keywords" in route_config and preview_text:
            text_lower = preview_text.lower()
            matched_keywords = sum(
                1
                for keyword in route_config["keywords"]
                if keyword.lower() in text_lower
            )

            if matched_keywords > 0:
                score += (matched_keywords / len(route_config["keywords"])) * 0.7

        # File size considerations
        file_size = file_path.stat().st_size
        if file_size < 100_000:  # Small files
            score += 0.1
        elif file_size > 5_000_000:  # Large files
            score -= 0.1

        return min(score, 1.0)

    def _extract_preview_text(self, file_path: Path, max_chars: int = 1000) -> str:
        """Extract preview text from document for routing"""
        try:
            if file_path.suffix.lower() == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read(max_chars)
            elif file_path.suffix.lower() == ".pdf":
                from PyPDF2 import PdfReader

                with open(file_path, "rb") as f:
                    pdf = PdfReader(f)
                    if pdf.pages:
                        return pdf.pages[0].extract_text()[:max_chars]
            # For other formats, return empty string (will rely on file extension)
            return ""
        except Exception:
            return ""


class DocumentAnalytics:
    """Document processing analytics and insights"""

    def __init__(self):
        self.analytics_db = Path(".docflow/analytics.json")
        self.load_analytics()

    def load_analytics(self):
        """Load analytics data"""
        if self.analytics_db.exists():
            with open(self.analytics_db, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {
                "processing_history": [],
                "model_performance": {},
                "document_types": {},
                "error_patterns": {},
                "processing_times": [],
            }

    def record_processing(self, result: Dict[str, Any]):
        """Record a processing event"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "file_name": result.get("file_name"),
            "document_type": result.get("document_type"),
            "model": result.get("ai_analysis", {}).get("model_name"),
            "success": result.get("ai_analysis", {}).get("success", False),
            "processing_time": result.get("processing_time"),
            "validation_passed": result.get("ai_analysis", {}).get("validation_passed"),
            "text_length": result.get("text_length"),
        }

        self.data["processing_history"].append(record)
        self._update_aggregations(record)
        self.save_analytics()

    def _update_aggregations(self, record: Dict[str, Any]):
        """Update aggregated analytics"""
        # Model performance
        model = record.get("model", "unknown")
        if model not in self.data["model_performance"]:
            self.data["model_performance"][model] = {
                "total_processed": 0,
                "successful": 0,
                "avg_processing_time": 0,
                "total_time": 0,
            }

        stats = self.data["model_performance"][model]
        stats["total_processed"] += 1
        if record.get("success"):
            stats["successful"] += 1
        if record.get("processing_time"):
            stats["total_time"] += record["processing_time"]
            stats["avg_processing_time"] = (
                stats["total_time"] / stats["total_processed"]
            )

        # Document types
        doc_type = record.get("document_type", "unknown")
        self.data["document_types"][doc_type] = (
            self.data["document_types"].get(doc_type, 0) + 1
        )

    def save_analytics(self):
        """Save analytics to disk"""
        self.analytics_db.parent.mkdir(parents=True, exist_ok=True)
        with open(self.analytics_db, "w") as f:
            json.dump(self.data, f, indent=2)

    def generate_insights_report(self) -> Dict[str, Any]:
        """Generate insights from analytics data"""
        if not self.data["processing_history"]:
            return {"message": "No processing history available"}

        recent_data = [
            record
            for record in self.data["processing_history"]
            if datetime.fromisoformat(record["timestamp"])
            > datetime.now() - timedelta(days=30)
        ]

        insights = {
            "summary": {
                "total_documents_processed": len(self.data["processing_history"]),
                "recent_documents": len(recent_data),
                "overall_success_rate": sum(
                    1 for r in self.data["processing_history"] if r.get("success")
                )
                / len(self.data["processing_history"]),
                "most_common_document_type": max(
                    self.data["document_types"], key=self.data["document_types"].get
                )
                if self.data["document_types"]
                else None,
            },
            "model_recommendations": self._generate_model_recommendations(),
            "optimization_suggestions": self._generate_optimization_suggestions(),
        }

        return insights

    def _generate_model_recommendations(self) -> List[Dict[str, Any]]:
        """Generate model performance recommendations"""
        recommendations = []

        for model, stats in self.data["model_performance"].items():
            success_rate = (
                stats["successful"] / stats["total_processed"]
                if stats["total_processed"] > 0
                else 0
            )

            if success_rate < 0.8 and stats["total_processed"] > 5:
                recommendations.append(
                    {
                        "type": "performance_warning",
                        "model": model,
                        "message": f"Model {model} has low success rate ({success_rate:.1%}). Consider switching models.",
                        "suggested_action": "Try openrouter-claude or openrouter-gemini-pro for better accuracy",
                    }
                )
            elif success_rate > 0.95 and stats["avg_processing_time"] < 10:
                recommendations.append(
                    {
                        "type": "performance_excellent",
                        "model": model,
                        "message": f"Model {model} shows excellent performance ({success_rate:.1%} success, {stats['avg_processing_time']:.1f}s avg)",
                        "suggested_action": "Consider using this model as default for similar document types",
                    }
                )

        return recommendations

    def _generate_optimization_suggestions(self) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []

        # Check for OCR usage patterns
        ocr_docs = [
            r
            for r in self.data["processing_history"]
            if "jpg" in r.get("file_name", "").lower()
            or "png" in r.get("file_name", "").lower()
        ]
        if len(ocr_docs) > 10:
            suggestions.append(
                "Consider using openrouter-pixtral for image documents - it's optimized for OCR"
            )

        # Check for large document processing
        large_docs = [
            r
            for r in self.data["processing_history"]
            if r.get("text_length", 0) > 50000
        ]
        if len(large_docs) > 5:
            suggestions.append(
                "For large documents, consider using openrouter-gemini-pro with its large context window"
            )

        # Check processing time patterns
        slow_processing = [
            r
            for r in self.data["processing_history"]
            if r.get("processing_time", 0) > 30
        ]
        if len(slow_processing) > len(self.data["processing_history"]) * 0.2:
            suggestions.append(
                "Consider using faster models like openrouter-gemini-flash for routine processing"
            )

        return suggestions


# CLI Commands for advanced features
@click.group()
def workflow():
    """📋 Advanced document workflow management"""
    pass


@workflow.command()
@click.argument("name")
@click.option(
    "--template",
    type=click.Choice(["invoice", "contract", "receipt", "custom"]),
    default="custom",
    help="Workflow template",
)
def create(name, template):
    """Create a new document processing workflow"""
    wf = DocumentWorkflow()

    templates = {
        "invoice": {
            "name": "Invoice Processing Workflow",
            "description": "Process invoices with validation and export",
            "steps": [
                {
                    "name": "Process Document",
                    "type": "process",
                    "model": "openrouter-claude",
                    "ocr": "auto",
                    "required_fields": ["invoice_number", "total_amount", "date"],
                },
                {
                    "name": "Validate Required Fields",
                    "type": "validate",
                    "required_fields": ["invoice_number", "total_amount", "date"],
                    "fail_on_missing": True,
                },
                {
                    "name": "Export to CSV",
                    "type": "export",
                    "format": "csv",
                    "output_file": "invoices.csv",
                },
            ],
        }
    }

    if template in templates:
        config = templates[template]
    else:
        config = {
            "name": f"Custom Workflow: {name}",
            "description": "Custom document processing workflow",
            "steps": [],
        }

    wf.create_workflow(name, config)


@workflow.command()
@click.argument("name")
@click.argument("input_path")
def run(name, input_path):
    """Run a document processing workflow"""
    wf = DocumentWorkflow()

    try:
        with console.status(f"[bold green]Running workflow '{name}'...") as status:
            results = wf.run_workflow(name, input_path)

        console.print(f"[green]✅ Workflow '{name}' completed successfully![/green]")

        # Display results
        results_table = Table(title="Workflow Results", box=box.ROUNDED)
        results_table.add_column("Step", style="cyan")
        results_table.add_column("Status", style="green")
        results_table.add_column("Output", style="blue")

        for i, result in enumerate(results.get("workflow_results", [])):
            status_icon = "✅" if result.get("success", True) else "❌"
            results_table.add_row(
                f"Step {i + 1}", status_icon, str(result.get("output_file", "N/A"))
            )

        console.print(results_table)

    except Exception as e:
        console.print(f"[red]❌ Workflow failed: {str(e)}[/red]")


@workflow.command()
def list():
    """List available workflows"""
    wf = DocumentWorkflow()
    workflows = wf.list_workflows()

    if not workflows:
        console.print(
            "[yellow]No workflows found. Create one with 'docflow workflow create <name>'[/yellow]"
        )
        return

    table = Table(title="Available Workflows", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("File", style="green")

    for workflow_name in workflows:
        table.add_row(workflow_name, f"{workflow_name}.yaml")

    console.print(table)


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--dry-run", is_flag=True, help="Show routing decisions without processing"
)
def smart_route(path, dry_run):
    """🧠 Intelligently route documents based on content analysis"""
    router = SmartDocumentRouter()
    path = Path(path)

    if path.is_file():
        files = [path]
    else:
        files = [
            f
            for f in path.rglob("*")
            if f.is_file()
            and f.suffix.lower() in [".pdf", ".docx", ".txt", ".jpg", ".png"]
        ]

    console.print(
        f"[blue]Analyzing {len(files)} documents for intelligent routing...[/blue]"
    )

    routing_results = []

    for file_path in track(files, description="Routing documents..."):
        route = router.route_document(str(file_path))
        routing_results.append(
            {
                "file": file_path.name,
                "route": route["name"],
                "model": route["config"].get("model", "unknown"),
                "confidence": route["confidence"],
                "output_dir": route["config"].get("output_dir", "./processed"),
            }
        )

    # Display routing results
    table = Table(title="🧠 Smart Document Routing Results", box=box.ROUNDED)
    table.add_column("Document", style="cyan")
    table.add_column("Route", style="green")
    table.add_column("Model", style="blue")
    table.add_column("Confidence", style="yellow")
    table.add_column("Output Dir", style="magenta")

    for result in routing_results:
        confidence_display = f"{result['confidence']:.1%}"
        if result["confidence"] > 0.8:
            confidence_display = f"[green]{confidence_display}[/green]"
        elif result["confidence"] > 0.5:
            confidence_display = f"[yellow]{confidence_display}[/yellow]"
        else:
            confidence_display = f"[red]{confidence_display}[/red]"

        table.add_row(
            result["file"],
            result["route"],
            result["model"],
            confidence_display,
            result["output_dir"],
        )

    console.print(table)

    if not dry_run and Confirm.ask("\nProceed with processing using these routes?"):
        # Actually process the documents
        console.print("[green]Processing documents with smart routing...[/green]")
        # Implementation would go here


@click.command()
def insights():
    """📊 Generate processing insights and recommendations"""
    analytics = DocumentAnalytics()
    insights = analytics.generate_insights_report()

    if "message" in insights:
        console.print(f"[yellow]{insights['message']}[/yellow]")
        return

    # Display summary
    summary_table = Table(title="📊 Processing Insights", box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary = insights["summary"]
    summary_table.add_row(
        "Total Documents Processed", str(summary["total_documents_processed"])
    )
    summary_table.add_row(
        "Recent Documents (30 days)", str(summary["recent_documents"])
    )
    summary_table.add_row(
        "Overall Success Rate", f"{summary['overall_success_rate']:.1%}"
    )
    summary_table.add_row(
        "Most Common Document Type", summary["most_common_document_type"] or "N/A"
    )

    console.print(summary_table)

    # Model recommendations
    if insights["model_recommendations"]:
        console.print("\n[bold yellow]🤖 Model Recommendations:[/bold yellow]")
        for rec in insights["model_recommendations"]:
            icon = "⚠️" if rec["type"] == "performance_warning" else "✅"
            console.print(f"{icon} {rec['message']}")
            console.print(f"   💡 {rec['suggested_action']}")

    # Optimization suggestions
    if insights["optimization_suggestions"]:
        console.print("\n[bold blue]⚡ Optimization Suggestions:[/bold blue]")
        for suggestion in insights["optimization_suggestions"]:
            console.print(f"• {suggestion}")


# Export commands
__all__ = ["workflow", "smart_route", "insights"]
