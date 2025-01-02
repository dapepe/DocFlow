#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source <(sed -e '/^#/d;/^\s*$/d' .env)
    set +a
else
    echo "Warning: .env file not found. Using default configuration."
fi

# Default port
PORT=${PORT:-8000}
HOST=${HOST:-"0.0.0.0"}

# Execute the serve command
python main.py serve --host "$HOST" --port "$PORT" 