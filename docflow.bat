@echo off
REM DocFlow CLI Wrapper Batch Script for Windows
REM Provides convenient access to DocFlow functionality

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
set "PYTHON_SCRIPT=%SCRIPT_DIR%main.py"

REM Check if Python script exists
if not exist "%PYTHON_SCRIPT%" (
    echo %RED%❌ Error: main.py not found in %SCRIPT_DIR%%NC%
    echo %YELLOW%💡 Make sure you're running this script from the DocFlow directory%NC%
    exit /b 1
)

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo %RED%❌ Error: Python not found%NC%
        echo %YELLOW%💡 Please install Python 3.11+ from https://python.org%NC%
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=py"
    )
) else (
    set "PYTHON_CMD=python"
)

REM Check Python version
for /f "tokens=2" %%a in ('%PYTHON_CMD% --version 2^>^&1') do set "PYTHON_VERSION=%%a"
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "PYTHON_MAJOR=%%a"
    set "PYTHON_MINOR=%%b"
)

if %PYTHON_MAJOR% LSS 3 (
    echo %RED%❌ Error: Python 3.11+ required (found %PYTHON_VERSION%)%NC%
    echo %YELLOW%💡 Please upgrade Python to use DocFlow%NC%
    pause
    exit /b 1
)
if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 11 (
    echo %RED%❌ Error: Python 3.11+ required (found %PYTHON_VERSION%)%NC%
    echo %YELLOW%💡 Please upgrade Python to use DocFlow%NC%
    pause
    exit /b 1
)

REM Check if virtual environment exists and activate it
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    echo %BLUE%🔧 Activating virtual environment...%NC%
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
) else if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    echo %BLUE%🔧 Activating virtual environment...%NC%
    call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
)

REM Check if .env file exists, create from template if not
set "ENV_FILE=%SCRIPT_DIR%.env"
set "TEMPLATE_FILE=%SCRIPT_DIR%env.template.txt"

if not exist "%ENV_FILE%" (
    if exist "%TEMPLATE_FILE%" (
        echo %YELLOW%⚙️  Creating .env file from template...%NC%
        copy "%TEMPLATE_FILE%" "%ENV_FILE%" >nul
        echo %GREEN%✅ .env file created. Please edit it with your API keys.%NC%
    )
)

goto :main

:show_banner
echo %CYAN%
echo ╔══════════════════════════════════════════════════════════════════════════════╗
echo ║                              🚀 DocFlow CLI                                 ║
echo ║                    Advanced AI-Powered Document Processing                  ║
echo ║                                                                              ║
echo ║  🎯 15+ AI Models  ^|  🔥 Smart Processing  ^|  ⚡ Enterprise Ready        ║
echo ╚══════════════════════════════════════════════════════════════════════════════╝
echo %NC%
goto :eof

:check_dependencies
echo %BLUE%🔍 Checking dependencies...%NC%

REM Check if requirements.txt exists
if exist "%SCRIPT_DIR%requirements.txt" (
    REM Check if key packages are installed
    %PYTHON_CMD% -c "import click, rich, fastapi, requests" >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%📦 Installing Python dependencies...%NC%
        %PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
        if errorlevel 1 (
            echo %RED%❌ Failed to install dependencies%NC%
            echo %YELLOW%💡 Try: pip install -r requirements.txt%NC%
            pause
            exit /b 1
        ) else (
            echo %GREEN%✅ Dependencies installed successfully%NC%
        )
    )
)

REM Check system dependencies
where poppler >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Warning: Poppler not found (required for PDF processing)%NC%
    echo %YELLOW%💡 Install from: https://github.com/oschwartz10612/poppler-windows%NC%
)
goto :eof

:show_quick_help
echo %PURPLE%📚 Quick Help:%NC%
echo.
echo %GREEN%Basic Usage:%NC%
echo   docflow.bat                           # Interactive mode
echo   docflow.bat process document.pdf     # Process single document  
echo   docflow.bat batch .\documents        # Batch process directory
echo   docflow.bat models                   # List available AI models
echo   docflow.bat serve                    # Start API server
echo.
echo %BLUE%Advanced Features:%NC%
echo   docflow.bat workflow create invoice  # Create processing workflow
echo   docflow.bat smart-route .\docs       # Intelligent document routing
echo   docflow.bat insights                 # Performance analytics
echo   docflow.bat help --topic models      # Detailed help on specific topics
echo.
echo %CYAN%Examples:%NC%
echo   docflow.bat process invoice.pdf --model openrouter-claude --verbose
echo   docflow.bat batch .\invoices --parallel 4 --model openrouter-gemini-flash
echo.
goto :eof

:handle_special_commands
set "cmd=%~1"

if "%cmd%"=="doctor" goto :doctor
if "%cmd%"=="check" goto :doctor
if "%cmd%"=="init" goto :init
if "%cmd%"=="setup" goto :init
if "%cmd%"=="update" goto :update
if "%cmd%"=="upgrade" goto :update
if "%cmd%"=="version" goto :version
if "%cmd%"=="-v" goto :version
if "%cmd%"=="--version" goto :version
if "%cmd%"=="help" goto :help
if "%cmd%"=="-h" goto :help
if "%cmd%"=="--help" goto :help
if "%cmd%"=="" goto :help

goto :not_special

:doctor
call :show_banner
echo %BLUE%🏥 DocFlow Doctor - System Health Check%NC%
echo.
call :check_dependencies

REM Check .env configuration
if exist "%ENV_FILE%" (
    echo %GREEN%✅ .env file found%NC%
    
    REM Check for API keys (without revealing them)
    findstr /C:"OPENROUTER_API_KEY=sk-or-" "%ENV_FILE%" >nul 2>&1
    if not errorlevel 1 (
        echo %GREEN%✅ OpenRouter API key configured%NC%
    ) else (
        findstr /C:"OPENAI_API_KEY=sk-" "%ENV_FILE%" >nul 2>&1
        if not errorlevel 1 (
            echo %GREEN%✅ OpenAI API key configured%NC%
        ) else (
            echo %YELLOW%⚠️  No API keys found in .env file%NC%
            echo %YELLOW%💡 Add API keys for cloud models or use local Ollama models%NC%
        )
    )
) else (
    echo %YELLOW%⚠️  .env file not found%NC%
)

REM Test basic functionality
echo %BLUE%🧪 Testing basic functionality...%NC%
%PYTHON_CMD% "%PYTHON_SCRIPT%" models --help >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ CLI test failed%NC%
) else (
    echo %GREEN%✅ CLI is functional%NC%
)

echo.
echo %GREEN%🎉 DocFlow health check complete!%NC%
pause
exit /b 0

:init
call :show_banner
echo %BLUE%🛠️  DocFlow Setup Wizard%NC%
echo.

REM Create .env from template if needed
if not exist "%ENV_FILE%" (
    if exist "%TEMPLATE_FILE%" (
        copy "%TEMPLATE_FILE%" "%ENV_FILE%" >nul
        echo %GREEN%✅ Created .env file from template%NC%
    )
)

REM Install dependencies
call :check_dependencies

REM Test models
echo %BLUE%🤖 Testing available models...%NC%
%PYTHON_CMD% "%PYTHON_SCRIPT%" models >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Some models may not be available (check API keys)%NC%
) else (
    echo %GREEN%✅ Models loading successfully%NC%
)

echo.
echo %GREEN%🎉 Setup complete! Try: docflow.bat%NC%
pause
exit /b 0

:update
echo %BLUE%📦 Updating DocFlow dependencies...%NC%
%PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt" --upgrade
echo %GREEN%✅ Update complete%NC%
pause
exit /b 0

:version
call :show_banner
echo %GREEN%DocFlow Version: 2.0%NC%
echo %BLUE%Python Version: %PYTHON_VERSION%%NC%
echo %PURPLE%Script Location: %SCRIPT_DIR%%NC%
pause
exit /b 0

:help
call :show_banner
call :show_quick_help
echo %CYAN%For detailed help: docflow.bat help --topic ^<topic^>%NC%
echo %CYAN%Available topics: getting-started, models, batch-processing, workflows, api%NC%
pause
exit /b 0

:not_special
goto :eof

:main
REM Handle special commands first
call :handle_special_commands "%~1"

REM If no arguments provided, show banner and run interactive mode
if "%~1"=="" (
    call :show_banner
    echo %GREEN%🚀 Starting DocFlow in interactive mode...%NC%
    echo.
)

REM Execute the Python CLI with all arguments
%PYTHON_CMD% "%PYTHON_SCRIPT%" %*
set "exit_code=%errorlevel%"

REM Show completion message for successful operations
if %exit_code% EQU 0 if not "%~1"=="" (
    echo.
    echo %GREEN%✅ DocFlow operation completed successfully!%NC%
)

if %exit_code% NEQ 0 (
    echo.
    echo %RED%❌ DocFlow operation failed with error code: %exit_code%%NC%
    pause
)

exit /b %exit_code%