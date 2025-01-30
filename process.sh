#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | sed '/^$/d' | sed 's/ *#.*//' | xargs)
else
    echo "Warning: .env file not found. Using default configuration."
fi

# Check if --dir flag is present
if [[ "$1" == "--dir" ]]; then
    if [ -z "$2" ]; then
        echo "Error: Directory path not provided"
        echo "Usage: ./process.sh --dir <directory_path>"
        exit 1
    fi
    
    directory="$2"
    if [ ! -d "$directory" ]; then
        echo "Error: Directory '$directory' does not exist"
        exit 1
    fi
    
    # Process all files in the directory
    for file in "$directory"/*.pdf; do
        if [ -f "$file" ]; then
            basename=$(basename "$file")
            dirname=$(dirname "$file")
            filename="${basename%.*}"
            output_file="$dirname/$filename.json"
            
            echo "Processing: $file -> $output_file"
            python main.py process "$file" --output "$output_file"
        fi
    done
else
    # Original behavior: Execute the process command with all arguments
    python main.py process "$@"
fi 