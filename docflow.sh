#!/bin/bash

# DocFlow CLI Wrapper Script
# Provides convenient access to DocFlow functionality

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/main.py"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}❌ Error: main.py not found in $SCRIPT_DIR${NC}"
    echo -e "${YELLOW}💡 Make sure you're running this script from the DocFlow directory${NC}"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Error: Python not found${NC}"
    echo -e "${YELLOW}💡 Please install Python 3.11+ to use DocFlow${NC}"
    exit 1
fi

# Determine Python command
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${RED}❌ Error: Python 3.11+ required (found $PYTHON_VERSION)${NC}"
    echo -e "${YELLOW}💡 Please upgrade Python to use DocFlow${NC}"
    exit 1
fi

# Check if virtual environment exists and activate it
VENV_DIR="$SCRIPT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
    source "$VENV_DIR/bin/activate"
elif [ -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Check if .env file exists, create from template if not
ENV_FILE="$SCRIPT_DIR/.env"
TEMPLATE_FILE="$SCRIPT_DIR/env.template.txt"

if [ ! -f "$ENV_FILE" ] && [ -f "$TEMPLATE_FILE" ]; then
    echo -e "${YELLOW}⚙️  Creating .env file from template...${NC}"
    cp "$TEMPLATE_FILE" "$ENV_FILE"
    echo -e "${GREEN}✅ .env file created. Please edit it with your API keys.${NC}"
fi

# Function to display banner
show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                              🚀 DocFlow CLI                                 ║"
    echo "║                    Advanced AI-Powered Document Processing                  ║"
    echo "║                                                                              ║"
    echo "║  🎯 15+ AI Models  |  🔥 Smart Processing  |  ⚡ Enterprise Ready        ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Function to check dependencies
check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"
    
    # Check if requirements.txt exists
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        # Check if key packages are installed
        if ! $PYTHON_CMD -c "import click, rich, fastapi, requests" 2>/dev/null; then
            echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
            $PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
            else
                echo -e "${RED}❌ Failed to install dependencies${NC}"
                echo -e "${YELLOW}💡 Try: pip install -r requirements.txt${NC}"
                exit 1
            fi
        fi
    fi
    
    # Check system dependencies
    if ! command -v pdftotext &> /dev/null; then
        echo -e "${YELLOW}⚠️  Warning: poppler-utils not found (required for PDF processing)${NC}"
        echo -e "${YELLOW}💡 Install with: brew install poppler (macOS) or apt-get install poppler-utils (Ubuntu)${NC}"
    fi
}

# Function to show quick help
show_quick_help() {
    echo -e "${PURPLE}📚 Quick Help:${NC}"
    echo ""
    echo -e "${GREEN}Basic Usage:${NC}"
    echo "  ./docflow.sh                           # Interactive mode"
    echo "  ./docflow.sh process document.pdf     # Process single document"
    echo "  ./docflow.sh batch ./documents        # Batch process directory"
    echo "  ./docflow.sh models                   # List available AI models"
    echo "  ./docflow.sh serve                    # Start API server"
    echo ""
    echo -e "${BLUE}Advanced Features:${NC}"
    echo "  ./docflow.sh workflow create invoice  # Create processing workflow"
    echo "  ./docflow.sh smart-route ./docs       # Intelligent document routing"
    echo "  ./docflow.sh insights                 # Performance analytics"
    echo "  ./docflow.sh help --topic models      # Detailed help on specific topics"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo "  ./docflow.sh process invoice.pdf --model openrouter-claude --verbose"
    echo "  ./docflow.sh batch ./invoices --parallel 4 --model openrouter-gemini-flash"
    echo ""
}

# Function to handle special commands
handle_special_commands() {
    case "$1" in
        "doctor"|"check")
            show_banner
            echo -e "${BLUE}🏥 DocFlow Doctor - System Health Check${NC}"
            echo ""
            check_dependencies
            
            # Check .env configuration
            if [ -f "$ENV_FILE" ]; then
                echo -e "${GREEN}✅ .env file found${NC}"
                
                # Check for API keys (without revealing them)
                if grep -q "OPENROUTER_API_KEY=sk-or-" "$ENV_FILE"; then
                    echo -e "${GREEN}✅ OpenRouter API key configured${NC}"
                elif grep -q "OPENAI_API_KEY=sk-" "$ENV_FILE"; then
                    echo -e "${GREEN}✅ OpenAI API key configured${NC}"
                else
                    echo -e "${YELLOW}⚠️  No API keys found in .env file${NC}"
                    echo -e "${YELLOW}💡 Add API keys for cloud models or use local Ollama models${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️  .env file not found${NC}"
            fi
            
            # Test basic functionality
            echo -e "${BLUE}🧪 Testing basic functionality...${NC}"
            if $PYTHON_CMD "$PYTHON_SCRIPT" models --help &>/dev/null; then
                echo -e "${GREEN}✅ CLI is functional${NC}"
            else
                echo -e "${RED}❌ CLI test failed${NC}"
            fi
            
            echo ""
            echo -e "${GREEN}🎉 DocFlow health check complete!${NC}"
            return 0
            ;;
        "init"|"setup")
            show_banner
            echo -e "${BLUE}🛠️  DocFlow Setup Wizard${NC}"
            echo ""
            
            # Create .env from template if needed
            if [ ! -f "$ENV_FILE" ] && [ -f "$TEMPLATE_FILE" ]; then
                cp "$TEMPLATE_FILE" "$ENV_FILE"
                echo -e "${GREEN}✅ Created .env file from template${NC}"
            fi
            
            # Install dependencies
            check_dependencies
            
            # Test models
            echo -e "${BLUE}🤖 Testing available models...${NC}"
            $PYTHON_CMD "$PYTHON_SCRIPT" models > /dev/null 2>&1 && echo -e "${GREEN}✅ Models loading successfully${NC}" || echo -e "${YELLOW}⚠️  Some models may not be available (check API keys)${NC}"
            
            echo ""
            echo -e "${GREEN}🎉 Setup complete! Try: ./docflow.sh${NC}"
            return 0
            ;;
        "update"|"upgrade")
            echo -e "${BLUE}📦 Updating DocFlow dependencies...${NC}"
            $PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt" --upgrade
            echo -e "${GREEN}✅ Update complete${NC}"
            return 0
            ;;
        "version"|"-v"|"--version")
            show_banner
            echo -e "${GREEN}DocFlow Version: 2.0${NC}"
            echo -e "${BLUE}Python Version: $PYTHON_VERSION${NC}"
            echo -e "${PURPLE}Script Location: $SCRIPT_DIR${NC}"
            return 0
            ;;
        "help"|"-h"|"--help"|"")
            show_banner
            show_quick_help
            echo -e "${CYAN}For detailed help: ./docflow.sh help --topic <topic>${NC}"
            echo -e "${CYAN}Available topics: getting-started, models, batch-processing, workflows, api${NC}"
            return 0
            ;;
    esac
    return 1
}

# Main execution
main() {
    # Handle special commands first
    if handle_special_commands "$1"; then
        exit 0
    fi
    
    # If no arguments provided, show banner and run interactive mode
    if [ $# -eq 0 ]; then
        show_banner
        echo -e "${GREEN}🚀 Starting DocFlow in interactive mode...${NC}"
        echo ""
    fi
    
    # Execute the Python CLI with all arguments
    $PYTHON_CMD "$PYTHON_SCRIPT" "$@"
    exit_code=$?
    
    # Show completion message for successful operations
    if [ $exit_code -eq 0 ] && [ $# -gt 0 ]; then
        echo ""
        echo -e "${GREEN}✅ DocFlow operation completed successfully!${NC}"
    fi
    
    exit $exit_code
}

# Run main function with all arguments
main "$@"