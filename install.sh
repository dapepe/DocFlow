#!/bin/bash

# DocFlow Installation Script
# Automates the setup process for DocFlow

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                          🚀 DocFlow Installation                            ║"
    echo "║                    Advanced AI-Powered Document Processing                  ║"
    echo "║                                                                              ║"
    echo "║               Setting up your document processing powerhouse...             ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_system() {
    echo -e "${BLUE}🔍 Checking system requirements...${NC}"
    
    # Check OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
        PACKAGE_MANAGER="brew"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
        if command -v apt-get &> /dev/null; then
            PACKAGE_MANAGER="apt-get"
        elif command -v yum &> /dev/null; then
            PACKAGE_MANAGER="yum"
        else
            PACKAGE_MANAGER="unknown"
        fi
    else
        OS="Unknown"
        PACKAGE_MANAGER="unknown"
    fi
    
    echo -e "${GREEN}✅ Operating System: $OS${NC}"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            echo -e "${GREEN}✅ Python: $PYTHON_VERSION${NC}"
            PYTHON_CMD="python3"
        else
            echo -e "${RED}❌ Python 3.11+ required (found $PYTHON_VERSION)${NC}"
            echo -e "${YELLOW}💡 Please install Python 3.11+ from https://python.org${NC}"
            exit 1
        fi
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        echo -e "${YELLOW}⚠️  Using 'python' command (version $PYTHON_VERSION)${NC}"
        PYTHON_CMD="python"
    else
        echo -e "${RED}❌ Python not found${NC}"
        echo -e "${YELLOW}💡 Please install Python 3.11+ from https://python.org${NC}"
        exit 1
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        echo -e "${RED}❌ pip not found${NC}"
        echo -e "${YELLOW}💡 Please install pip${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ pip: Available${NC}"
}

install_system_dependencies() {
    echo -e "${BLUE}📦 Installing system dependencies...${NC}"
    
    case $PACKAGE_MANAGER in
        "brew")
            if ! command -v brew &> /dev/null; then
                echo -e "${YELLOW}⚠️  Homebrew not found. Installing...${NC}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            echo -e "${BLUE}Installing poppler for PDF processing...${NC}"
            brew install poppler || true
            ;;
        "apt-get")
            echo -e "${BLUE}Installing poppler-utils for PDF processing...${NC}"
            sudo apt-get update
            sudo apt-get install -y poppler-utils
            ;;
        "yum")
            echo -e "${BLUE}Installing poppler-utils for PDF processing...${NC}"
            sudo yum install -y poppler-utils
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown package manager. Please install poppler manually:${NC}"
            echo -e "${YELLOW}   - macOS: brew install poppler${NC}"
            echo -e "${YELLOW}   - Ubuntu: sudo apt-get install poppler-utils${NC}"
            echo -e "${YELLOW}   - CentOS: sudo yum install poppler-utils${NC}"
            ;;
    esac
}

create_virtual_environment() {
    echo -e "${BLUE}🔧 Setting up Python virtual environment...${NC}"
    
    VENV_DIR="$SCRIPT_DIR/venv"
    
    if [ -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Virtual environment already exists. Removing old one...${NC}"
        rm -rf "$VENV_DIR"
    fi
    
    $PYTHON_CMD -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    echo -e "${GREEN}✅ Virtual environment created${NC}"
}

install_python_dependencies() {
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
    
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
        echo -e "${GREEN}✅ Python dependencies installed${NC}"
    else
        echo -e "${RED}❌ requirements.txt not found${NC}"
        exit 1
    fi
}

setup_configuration() {
    echo -e "${BLUE}⚙️  Setting up configuration...${NC}"
    
    ENV_FILE="$SCRIPT_DIR/.env"
    TEMPLATE_FILE="$SCRIPT_DIR/env.template.txt"
    
    if [ ! -f "$ENV_FILE" ] && [ -f "$TEMPLATE_FILE" ]; then
        cp "$TEMPLATE_FILE" "$ENV_FILE"
        echo -e "${GREEN}✅ Created .env file from template${NC}"
        
        echo -e "${YELLOW}💡 Please edit .env file with your API keys:${NC}"
        echo -e "${CYAN}   - OpenRouter API key (recommended): OPENROUTER_API_KEY=sk-or-v1-your-key${NC}"
        echo -e "${CYAN}   - OpenAI API key: OPENAI_API_KEY=sk-your-key${NC}"
        echo -e "${CYAN}   - Mistral API key: MISTRAL_API_KEY=your-key${NC}"
    fi
    
    # Create directories
    mkdir -p "$SCRIPT_DIR/.docflow"
    mkdir -p "$SCRIPT_DIR/output"
    mkdir -p "$SCRIPT_DIR/processed"
    
    echo -e "${GREEN}✅ Configuration setup complete${NC}"
}

test_installation() {
    echo -e "${BLUE}🧪 Testing installation...${NC}"
    
    # Test CLI
    if $PYTHON_CMD "$SCRIPT_DIR/main.py" --version &>/dev/null; then
        echo -e "${GREEN}✅ CLI is functional${NC}"
    else
        echo -e "${RED}❌ CLI test failed${NC}"
        exit 1
    fi
    
    # Test models (basic)
    if $PYTHON_CMD "$SCRIPT_DIR/main.py" models --help &>/dev/null; then
        echo -e "${GREEN}✅ Models command working${NC}"
    else
        echo -e "${YELLOW}⚠️  Models command issues (may need API keys)${NC}"
    fi
}

show_completion() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                          🎉 Installation Complete!                          ║"
    echo "║                                                                              ║"
    echo "║  DocFlow is now ready to process your documents with AI-powered analysis!   ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${CYAN}🚀 Next Steps:${NC}"
    echo -e "${BLUE}1. ${NC}Edit your API keys: ${YELLOW}nano .env${NC}"
    echo -e "${BLUE}2. ${NC}Try interactive mode: ${YELLOW}./docflow.sh${NC}"
    echo -e "${BLUE}3. ${NC}Process a document: ${YELLOW}./docflow.sh process document.pdf${NC}"
    echo -e "${BLUE}4. ${NC}Get help: ${YELLOW}./docflow.sh help${NC}"
    echo ""
    
    echo -e "${PURPLE}📚 Documentation:${NC}"
    echo -e "${BLUE}• ${NC}README.md - Complete feature overview"
    echo -e "${BLUE}• ${NC}docs/OPENROUTER_INTEGRATION.md - Model selection guide"
    echo -e "${BLUE}• ${NC}docs/CLI_ENHANCEMENTS.md - Advanced CLI features"
    echo ""
    
    echo -e "${GREEN}Happy document processing! 🚀${NC}"
}

main() {
    show_banner
    
    echo -e "${YELLOW}This script will install DocFlow and all its dependencies.${NC}"
    echo -e "${YELLOW}You may be prompted for administrator password for system packages.${NC}"
    echo ""
    
    read -p "Continue with installation? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Installation cancelled.${NC}"
        exit 0
    fi
    
    check_system
    install_system_dependencies
    create_virtual_environment
    install_python_dependencies
    setup_configuration
    test_installation
    show_completion
}

# Run main function
main "$@"