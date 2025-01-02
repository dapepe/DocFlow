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
            verbose_mode = os.getenv('DOCFLOW_LOG_LEVEL', 'ERROR') == 'DEBUG'

            # Configure handlers
            if verbose_mode:
                # In verbose mode, show all levels in console
                config['handlers']['console']['level'] = 'DEBUG'
            else:
                # In normal mode, only show ERROR and above
                config['handlers']['console']['level'] = 'ERROR'

            # Configure file handler to always capture all logs
            config['handlers']['file']['level'] = 'DEBUG'

            # Update log levels for docflow loggers
            for logger_name, logger_config in config.get('loggers', {}).items():
                if logger_name.startswith('docflow'):
                    logger_config['level'] = 'DEBUG' if verbose_mode else 'ERROR'

            logging.config.dictConfig(config)
    except Exception as e:
        # Fallback to basic configuration
        console_level = 'DEBUG' if os.getenv('DOCFLOW_LOG_LEVEL') == 'DEBUG' else 'ERROR'
        logging.basicConfig(
            level=console_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.warning(f"Error loading logging configuration: {e}")