from pathlib import Path
from typing import Set

def get_supported_extensions() -> Set[str]:
    """Return set of supported file extensions"""
    return {'.pdf', '.docx', '.txt'}

def validate_file_path(file_path: str) -> bool:
    """Validate if file exists and has supported extension"""
    path = Path(file_path)
    return path.exists() and path.suffix.lower() in get_supported_extensions()

def format_file_size(size_in_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"
