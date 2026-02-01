@echo off
REM DocFlow Installation Script for Windows
REM Automates the setup process for DocFlow

setlocal EnableDelayedExpansion

REM Colors for output (Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "PURPLE=[95m"
set "CYAN=[96m"
set "NC=[0m"

REM Get script directory
set "SCRIPT_DIR=%~dp0"

call :show_banner

echo %YELLOW%This script will install DocFlow and all its dependencies.%NC%
echo %YELLOW%Please run as Administrator if prompted.%NC%
echo.

set /p "choice=Continue with installation? (y/N): "
if /i not "%choice%"=="y" (
    echo %YELLOW%Installation cancelled.%NC%
    pause
    exit /b 0
)

call :check_system
call :install_python_dependencies
call :setup_configuration
call :test_installation
call :show_completion

pause
exit /b 0

:show_banner
echo %CYAN%
echo ╔══════════════════════════════════════════════════════════════════════════════╗
echo ║                          🚀 DocFlow Installation                            ║
echo ║                    Advanced AI-Powered Document Processing                  ║
echo ║                                                                              ║
echo ║               Setting up your document processing powerhouse...             ║
echo ╚══════════════════════════════════════════════════════════════════════════════╝
echo %NC%
goto :eof

:check_system
echo %BLUE%🔍 Checking system requirements...%NC%

REM Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo %GREEN%✅ Windows Version: %VERSION%%NC%

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo %RED%❌ Python not found%NC%
        echo %YELLOW%💡 Please install Python 3.11+ from https://python.org%NC%
        echo %YELLOW%   Make sure to check "Add Python to PATH" during installation%NC%
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=py"
        for /f "tokens=2" %%a in ('py --version 2^>^&1') do set "PYTHON_VERSION=%%a"
    )
) else (
    set "PYTHON_CMD=python"
    for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%a"
)

echo %GREEN%✅ Python: %PYTHON_VERSION%%NC%

REM Check Python version
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "PYTHON_MAJOR=%%a"
    set "PYTHON_MINOR=%%b"
)

if %PYTHON_MAJOR% LSS 3 (
    echo %RED%❌ Python 3.11+ required (found %PYTHON_VERSION%)%NC%
    echo %YELLOW%💡 Please upgrade Python from https://python.org%NC%
    pause
    exit /b 1
)
if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 11 (
    echo %RED%❌ Python 3.11+ required (found %PYTHON_VERSION%)%NC%
    echo %YELLOW%💡 Please upgrade Python from https://python.org%NC%
    pause
    exit /b 1
)

REM Check pip
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ pip not found%NC%
    echo %YELLOW%💡 Please install pip%NC%
    pause
    exit /b 1
) else (
    echo %GREEN%✅ pip: Available%NC%
)

REM Check for poppler (optional)
where poppler >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Poppler not found (required for PDF processing)%NC%
    echo %YELLOW%💡 Download from: https://github.com/oschwartz10612/poppler-windows%NC%
    echo %YELLOW%   Extract and add to PATH, or install via conda: conda install poppler%NC%
) else (
    echo %GREEN%✅ Poppler: Available%NC%
)

goto :eof

:create_virtual_environment
echo %BLUE%🔧 Setting up Python virtual environment...%NC%

set "VENV_DIR=%SCRIPT_DIR%venv"

if exist "%VENV_DIR%" (
    echo %YELLOW%Virtual environment already exists. Removing old one...%NC%
    rmdir /s /q "%VENV_DIR%"
)

%PYTHON_CMD% -m venv "%VENV_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"

REM Upgrade pip
python -m pip install --upgrade pip

echo %GREEN%✅ Virtual environment created%NC%
goto :eof

:install_python_dependencies
echo %BLUE%📦 Installing Python dependencies...%NC%

if exist "%SCRIPT_DIR%requirements.txt" (
    REM Check if we should create virtual environment
    echo.
    set /p "use_venv=Create virtual environment? (recommended) (Y/n): "
    if /i not "!use_venv!"=="n" (
        call :create_virtual_environment
    )
    
    %PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 (
        echo %RED%❌ Failed to install dependencies%NC%
        echo %YELLOW%💡 Try running as Administrator or check your internet connection%NC%
        pause
        exit /b 1
    )
    echo %GREEN%✅ Python dependencies installed%NC%
) else (
    echo %RED%❌ requirements.txt not found%NC%
    pause
    exit /b 1
)
goto :eof

:setup_configuration
echo %BLUE%⚙️  Setting up configuration...%NC%

set "ENV_FILE=%SCRIPT_DIR%.env"
set "TEMPLATE_FILE=%SCRIPT_DIR%env.template.txt"

if not exist "%ENV_FILE%" (
    if exist "%TEMPLATE_FILE%" (
        copy "%TEMPLATE_FILE%" "%ENV_FILE%" >nul
        echo %GREEN%✅ Created .env file from template%NC%
        
        echo %YELLOW%💡 Please edit .env file with your API keys:%NC%
        echo %CYAN%   - OpenRouter API key (recommended): OPENROUTER_API_KEY=sk-or-v1-your-key%NC%
        echo %CYAN%   - OpenAI API key: OPENAI_API_KEY=sk-your-key%NC%
        echo %CYAN%   - Mistral API key: MISTRAL_API_KEY=your-key%NC%
    )
)

REM Create directories
if not exist "%SCRIPT_DIR%.docflow" mkdir "%SCRIPT_DIR%.docflow"
if not exist "%SCRIPT_DIR%output" mkdir "%SCRIPT_DIR%output"
if not exist "%SCRIPT_DIR%processed" mkdir "%SCRIPT_DIR%processed"

echo %GREEN%✅ Configuration setup complete%NC%
goto :eof

:test_installation
echo %BLUE%🧪 Testing installation...%NC%

REM Test CLI
%PYTHON_CMD% "%SCRIPT_DIR%main.py" --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ CLI test failed%NC%
    pause
    exit /b 1
) else (
    echo %GREEN%✅ CLI is functional%NC%
)

REM Test models (basic)
%PYTHON_CMD% "%SCRIPT_DIR%main.py" models --help >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Models command issues (may need API keys)%NC%
) else (
    echo %GREEN%✅ Models command working%NC%
)

goto :eof

:show_completion
echo %GREEN%
echo ╔══════════════════════════════════════════════════════════════════════════════╗
echo ║                          🎉 Installation Complete!                          ║
echo ║                                                                              ║
echo ║  DocFlow is now ready to process your documents with AI-powered analysis!   ║
echo ╚══════════════════════════════════════════════════════════════════════════════╝
echo %NC%

echo %CYAN%🚀 Next Steps:%NC%
echo %BLUE%1. %NC%Edit your API keys: %YELLOW%notepad .env%NC%
echo %BLUE%2. %NC%Try interactive mode: %YELLOW%docflow.bat%NC%
echo %BLUE%3. %NC%Process a document: %YELLOW%docflow.bat process document.pdf%NC%
echo %BLUE%4. %NC%Get help: %YELLOW%docflow.bat help%NC%
echo.

echo %PURPLE%📚 Documentation:%NC%
echo %BLUE%• %NC%README.md - Complete feature overview
echo %BLUE%• %NC%docs\OPENROUTER_INTEGRATION.md - Model selection guide
echo %BLUE%• %NC%docs\CLI_ENHANCEMENTS.md - Advanced CLI features
echo.

echo %GREEN%Happy document processing! 🚀%NC%
goto :eof