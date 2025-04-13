import logging
import os
from datetime import datetime
from pathlib import Path

def get_logger(name, log_file=None):
    """Get a logger with enhanced settings for autonomous operation."""
    # Check if logger already exists to avoid duplicate handlers
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    # Set log level
    logger.setLevel(logging.INFO)
    
    # Find project root directory
    project_root = _find_project_root()
    
    # Create logs directory at project root if it doesn't exist
    logs_dir = os.path.join(project_root, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Use a session-specific log file in the logs directory
    if not log_file:
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(logs_dir, f"bibot_session_{date_str}.log")
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def _find_project_root():
    """
    Find the project root directory by looking for marker files
    
    Returns:
        str: The path to the project root
    """
    # Start with the current file's directory
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # In Docker, the app directory is likely /app
    if os.path.exists('/app'):
        return '/app'
    
    # Walk up the directory tree until we find a marker file
    markers = ['.git', 'pyproject.toml', 'poetry.lock']
    
    while current_dir != current_dir.parent:
        for marker in markers:
            if (current_dir / marker).exists():
                return str(current_dir)
        current_dir = current_dir.parent
    
    # If we can't find the project root, just use the current working directory
    return os.getcwd()