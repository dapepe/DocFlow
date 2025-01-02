import yaml
import logging.config
import os
from pathlib import Path

def setup_logging(config_path: str = "config/logging.yaml"):
    """Setup logging configuration with dynamic log level support"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

            # Get log level from environment variable
            log_level = os.getenv('DOCFLOW_LOG_LEVEL', 'INFO')

            # Update log levels for docflow loggers
            for logger_name, logger_config in config.get('loggers', {}).items():
                if logger_name.startswith('docflow'):
                    logger_config['level'] = log_level

            logging.config.dictConfig(config)
    except Exception as e:
        # Fallback to basic configuration
        logging.basicConfig(
            level=os.getenv('DOCFLOW_LOG_LEVEL', 'INFO'),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.warning(f"Error loading logging configuration: {e}")