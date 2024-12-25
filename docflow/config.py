import yaml
import logging.config
from pathlib import Path

def setup_logging(config_path: str = "config/logging.yaml"):
    """Setup logging configuration"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)
    except Exception as e:
        # Fallback to basic configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.warning(f"Error loading logging configuration: {e}")
