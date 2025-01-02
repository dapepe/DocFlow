#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    # Direct source of the .env file
    export $(grep -v '^#' .env | sed '/^$/d' | sed 's/ *#.*//' | xargs)
    # Debug output to verify loading
    echo "Environment variables loaded:"
    echo "PRIMARY_MODEL=${PRIMARY_MODEL:-not set}"
    echo "OPENAI_API_KEY=${OPENAI_API_KEY:+is set}"
    echo "OLLAMA_HOST=${OLLAMA_HOST:-not set}"
else
    echo "Warning: .env file not found. Using default configuration."
fi

# Default port
PORT=${PORT:-8000}
HOST=${HOST:-"0.0.0.0"}

# Execute the serve command
python main.py serve --host "$HOST" --port "$PORT" 