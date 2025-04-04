import logging
from app.config import load_config

def get_logger(name=None):
    """Configure and return a logger"""
    config = load_config()
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Set up logging format and level
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Set log level from config
        log_level = getattr(logging, config.logging.log_level)
        logger.setLevel(log_level)
    
    return logger