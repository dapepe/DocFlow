import sys
from docflow.cli import cli
from docflow.config import setup_logging

if __name__ == "__main__":
    setup_logging()
    cli(sys.argv[1:])
