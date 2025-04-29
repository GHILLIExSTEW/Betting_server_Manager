import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from bot.config.settings import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Sets up a logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create formatters
    file_formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    console_formatter = logging.Formatter(
        fmt='%(levelname)s - %(message)s'
    )

    # Create and configure file handler
    log_file = LOGS_DIR / f"{name}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)

    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def get_logger(name: str) -> logging.Logger:
    """Gets or creates a logger instance"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Convert string log level to int
        level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        logger = setup_logger(name, level)
    return logger

# Set up root logger
root_logger = get_logger('betting_bot')
root_logger.info("Logging system initialized") 