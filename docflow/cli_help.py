"""
Enhanced CLI Help System with Examples and Best Practices
"""
import click
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from rich import box
from rich.syntax import Syntax

console = Console()

@click.command()
@click.option('--topic', '-t', type=click.Choice([
    'getting-started', 'models', 'batch-processing', 'workflows', 
    'api', 'performance', 'troubleshooting', 'examples'
]), help="Get help on a specific topic")
def help(topic):
    """📚 Comprehensive help and documentation"""
    
    if not topic:
        show_main_help()
    elif topic == 'getting-started':
        show_getting_started()
    elif topic == 'models':
        show_models_help()
    elif topic == 'batch-processing':
        show_batch_help()
    elif topic == 'workflows':
        show_workflows_help()
    elif topic == 'api':
        show_api_help()
    elif topic == 'performance':
        show_performance_help()
    elif topic == 'troubleshooting':
        show_troubleshooting()
    elif topic == 'examples':
        show_examples()

def show_main_help():
    """Show main help overview"""
    console.print(Panel(
        "[bold cyan]📚 DocFlow Help System[/bold cyan]\n\n"
        "DocFlow is an advanced AI-powered document processing system that supports\n"
        "15+ AI models, smart processing workflows, and enterprise-grade features.\n\n"
        "[bold]Quick Start:[/bold]\n"
        "• docflow process document.pdf\n"
        "• docflow batch ./documents --parallel 4\n"
        "• docflow models --detailed\n"
        "• docflow serve --port 8080",
        title="DocFlow Help"
    ))
    
    # Help topics table
    topics_table = Table(title="📖 Available Help Topics", box=box.ROUNDED)
    topics_table.add_column("Topic", style="cyan", width=20)
    topics_table.add_column("Description", style="green")
    topics_table.add_column("Command", style="blue")
    
    help_topics = [
        ("getting-started", "Installation and basic usage", "docflow help --topic getting-started"),
        ("models", "AI models and selection guide", "docflow help --topic models"),
        ("batch-processing", "Process multiple documents", "docflow help --topic batch-processing"),
        ("workflows", "Advanced workflow automation", "docflow help --topic workflows"),
        ("api", "REST API usage and endpoints", "docflow help --topic api"),
        ("performance", "Optimization and monitoring", "docflow help --topic performance"),
        ("troubleshooting", "Common issues and solutions", "docflow help --topic troubleshooting"),
        ("examples", "Real-world usage examples", "docflow help --topic examples")
    ]
    
    for topic, desc, cmd in help_topics:
        topics_table.add_row(topic, desc, cmd)
    
    console.print(topics_table)

def show_getting_started():
    """Show getting started guide"""
    console.print(Panel("[bold cyan]🚀 Getting Started with DocFlow[/bold cyan]", expand=False))
    
    steps = [
        ("1. Installation", [
            "pip install -r requirements.txt",
            "# Install system dependencies (poppler)",
            "brew install poppler  # macOS",
            "apt-get install poppler-utils  # Ubuntu"
        ]),
        ("2. Configuration", [
            "cp env.template.txt .env",
            "# Edit .env with your API keys",
            "OPENROUTER_API_KEY=sk-or-v1-your-key",
            "PRIMARY_MODEL=openrouter-gemini-flash"
        ]),
        ("3. Basic Usage", [
            "# Process single document",
            "docflow process invoice.pdf",
            "",
            "# Interactive mode (recommended for beginners)",
            "docflow",
            "",
            "# Get model information",
            "docflow models --detailed"
        ]),
        ("4. Advanced Features", [
            "# Batch processing",
            "docflow batch ./documents --parallel 4",
            "",
            "# Smart routing",
            "docflow smart-route ./documents",
            "",
            "# Performance insights",
            "docflow insights"
        ])
    ]
    
    for title, commands in steps:
        console.print(f"\n[bold blue]{title}:[/bold blue]")
        code = "\n".join(commands)
        syntax = Syntax(code, "bash", theme="monokai", line_numbers=False)
        console.print(syntax)

def show_models_help():
    """Show models help and selection guide"""
    console.print(Panel("[bold cyan]🤖 AI Models Selection Guide[/bold cyan]", expand=False))
    
    # Model tiers
    tiers = [
        ("🥇 Premium Tier", [
            ("openrouter-claude", "Best reasoning, complex documents, legal/contracts"),
            ("openrouter-gpt4-vision", "Superior OCR, technical documents, forms")
        ]),
        ("🥈 Balanced Tier", [
            ("openrouter-gemini-flash", "Fast, cost-effective, general purpose (RECOMMENDED)"),
            ("openrouter-qwen-vl", "Multilingual documents, international business")
        ]),
        ("🥉 Specialized Tier", [
            ("openrouter-pixtral", "OCR specialist, scanned documents, images"),
            ("qwen-vision", "Local processing, offline capability")
        ])
    ]
    
    for tier_name, models in tiers:
        console.print(f"\n[bold yellow]{tier_name}[/bold yellow]")
        for model_id, description in models:
            console.print(f"  • [cyan]{model_id}[/cyan]: {description}")
    
    # Usage recommendations
    console.print("\n[bold blue]💡 Model Selection Guide:[/bold blue]")
    recommendations = Table(box=box.MINIMAL)
    recommendations.add_column("Document Type", style="cyan")
    recommendations.add_column("Recommended Model", style="green")
    recommendations.add_column("Alternative", style="yellow")
    
    recs = [
        ("Invoices/Bills", "openrouter-claude", "openrouter-gemini-flash"),
        ("Contracts/Legal", "openrouter-claude", "openrouter-gpt4-vision"),
        ("Scanned Documents", "openrouter-pixtral", "openrouter-gpt4-vision"),
        ("Multilingual", "openrouter-qwen-vl", "openrouter-claude"),
        ("High Volume/Batch", "openrouter-gemini-flash", "qwen-vision"),
        ("Complex Analysis", "openrouter-claude", "openrouter-gpt4-vision")
    ]
    
    for doc_type, primary, alt in recs:
        recommendations.add_row(doc_type, primary, alt)
    
    console.print(recommendations)

def show_batch_help():
    """Show batch processing help"""
    console.print(Panel("[bold cyan]📁 Batch Processing Guide[/bold cyan]", expand=False))
    
    examples = [
        ("Basic Batch Processing", "docflow batch ./documents"),
        ("Parallel Processing", "docflow batch ./documents --parallel 8"),
        ("Specific File Types", "docflow batch ./docs --formats pdf docx txt"),
        ("Recursive Processing", "docflow batch ./root --recursive"),
        ("Custom Output Directory", "docflow batch ./docs --output-dir ./processed"),
        ("Resume Interrupted Batch", "docflow batch ./docs --resume"),
        ("Smart Model Selection", "docflow batch ./docs --model auto")
    ]
    
    for title, command in examples:
        console.print(f"\n[bold blue]{title}:[/bold blue]")
        console.print(f"  [dim]$ {command}[/dim]")
    
    # Performance tips
    console.print(f"\n[bold yellow]⚡ Performance Tips:[/bold yellow]")
    tips = [
        "Use --parallel 4-8 for optimal performance (adjust based on your CPU)",
        "openrouter-gemini-flash is fastest for high-volume processing",
        "Use --resume to continue interrupted batch jobs",
        "Process images separately with openrouter-pixtral for better OCR",
        "Large documents (>5MB) work best with openrouter-gemini-pro"
    ]
    
    for tip in tips:
        console.print(f"  • {tip}")

def show_workflows_help():
    """Show workflows help"""
    console.print(Panel("[bold cyan]📋 Workflow Automation Guide[/bold cyan]", expand=False))
    
    console.print("[bold blue]Creating Workflows:[/bold blue]")
    console.print("  docflow workflow create invoice-processing --template invoice")
    console.print("  docflow workflow create custom-flow --template custom")
    
    console.print("\n[bold blue]Running Workflows:[/bold blue]")
    console.print("  docflow workflow run invoice-processing ./invoices/")
    console.print("  docflow workflow list")
    
    console.print("\n[bold blue]Smart Document Routing:[/bold blue]")
    console.print("  docflow smart-route ./documents  # Preview routing decisions")
    console.print("  docflow smart-route ./documents --dry-run=false  # Execute routing")
    
    # Workflow template example
    console.print(f"\n[bold yellow]📄 Sample Workflow Configuration:[/bold yellow]")
    workflow_yaml = '''name: Invoice Processing Workflow
description: Process invoices with validation and export
steps:
  - name: Process Document
    type: process
    model: openrouter-claude
    ocr: auto
    required_fields: [invoice_number, total_amount, date]
  
  - name: Validate Required Fields
    type: validate
    required_fields: [invoice_number, total_amount, date]
    fail_on_missing: true
  
  - name: Export to CSV
    type: export
    format: csv
    output_file: invoices.csv'''
    
    syntax = Syntax(workflow_yaml, "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)

def show_performance_help():
    """Show performance optimization help"""
    console.print(Panel("[bold cyan]⚡ Performance Optimization Guide[/bold cyan]", expand=False))
    
    console.print("[bold blue]Monitoring Performance:[/bold blue]")
    console.print("  docflow insights        # Get processing analytics")
    console.print("  docflow stats           # Show performance dashboard")
    console.print("  curl localhost:8000/performance  # API performance stats")
    
    console.print("\n[bold blue]Optimization Strategies:[/bold blue]")
    
    strategies = [
        ("Model Selection", [
            "Use openrouter-gemini-flash for high-volume processing",
            "Use openrouter-claude only for complex documents",
            "Use qwen-vision for offline/local processing"
        ]),
        ("Batch Processing", [
            "Set optimal parallelism: --parallel 4-8",
            "Group similar documents together",
            "Use --resume for large batch jobs"
        ]),
        ("Caching", [
            "Enable response caching (automatic)",
            "Process similar documents together for cache hits",
            "Cache is optimized for text-only requests"
        ]),
        ("API Configuration", [
            "Use appropriate timeouts for large documents",
            "Configure retry logic for reliability",
            "Monitor rate limits on external APIs"
        ])
    ]
    
    for category, tips in strategies:
        console.print(f"\n[bold yellow]{category}:[/bold yellow]")
        for tip in tips:
            console.print(f"  • {tip}")

def show_troubleshooting():
    """Show troubleshooting guide"""
    console.print(Panel("[bold cyan]🔧 Troubleshooting Guide[/bold cyan]", expand=False))
    
    issues = [
        ("Model Not Available", [
            "Check API keys in .env file",
            "Verify internet connection for cloud models",
            "Run 'docflow models --test-connection'",
            "Try fallback model for testing"
        ]),
        ("Processing Errors", [
            "Enable verbose logging: --verbose",
            "Check document format compatibility",
            "Try different model if one fails",
            "Reduce document size if too large"
        ]),
        ("Performance Issues", [
            "Reduce batch size: --parallel 2",
            "Use faster models like gemini-flash",
            "Check system resources (CPU/memory)",
            "Clear cache: rm -rf .docflow/cache"
        ]),
        ("API Connection Issues", [
            "Verify API keys are correct",
            "Check firewall/proxy settings",
            "Test with curl to verify connectivity",
            "Try different model provider"
        ])
    ]
    
    for issue, solutions in issues:
        console.print(f"\n[bold red]❌ {issue}:[/bold red]")
        for solution in solutions:
            console.print(f"  • {solution}")

def show_examples():
    """Show real-world examples"""
    console.print(Panel("[bold cyan]🎯 Real-World Usage Examples[/bold cyan]", expand=False))
    
    examples = [
        ("Invoice Processing Workflow", [
            "# Process invoices with validation",
            "docflow process invoice.pdf --model openrouter-claude",
            "# Batch process invoice folder",
            "docflow batch ./invoices --model openrouter-claude --parallel 4",
            "# Export results to accounting system",
            "python -c \"import json; data=json.load(open('results.json')); print(data['total_amount'])\""
        ]),
        ("Document Classification System", [
            "# Smart route documents by type",
            "docflow smart-route ./mixed-documents",
            "# Process with type-specific models",
            "docflow batch ./contracts --model openrouter-claude",
            "docflow batch ./receipts --model openrouter-pixtral --use-ocr"
        ]),
        ("Multilingual Document Processing", [
            "# Process Chinese/Japanese documents",
            "docflow process chinese_contract.pdf --model openrouter-qwen-vl",
            "# Batch process multilingual folder",
            "docflow batch ./international --model openrouter-qwen-vl"
        ]),
        ("High-Volume Processing", [
            "# Process thousands of documents efficiently",
            "docflow batch ./archive --model openrouter-gemini-flash --parallel 8",
            "# Resume interrupted processing",
            "docflow batch ./archive --resume",
            "# Monitor progress",
            "docflow insights"
        ]),
        ("API Integration", [
            "# Start API server",
            "docflow serve --port 8080",
            "# Process via API",
            "curl -X POST localhost:8080/process -F file=@doc.pdf -F model=openrouter-claude",
            "# Batch process via API",
            "curl -X POST localhost:8080/batch-process -F files=@doc1.pdf -F files=@doc2.pdf"
        ])
    ]
    
    for title, commands in examples:
        console.print(f"\n[bold blue]{title}:[/bold blue]")
        code = "\n".join(commands)
        syntax = Syntax(code, "bash", theme="monokai", line_numbers=False)
        console.print(syntax)

# Add to main CLI
def add_help_command(cli_group):
    """Add enhanced help command to CLI"""
    cli_group.add_command(help)