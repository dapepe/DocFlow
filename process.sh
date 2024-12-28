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

# Execute the process command with all arguments passed to the script
python main.py process "$@" 