#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | sed '/^$/d' | sed 's/ *#.*//' | xargs)
else
    echo "Warning: .env file not found. Using default configuration."
fi

# Execute the process command with all arguments passed to the script
python main.py process "$@" 