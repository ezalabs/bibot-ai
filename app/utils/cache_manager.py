import json
import os
from app.utils.logger import get_logger
from pathlib import Path

# Configure logging
logger = get_logger()


class CacheManager:
    """
    A generic cache manager for storing and retrieving data from local files.
    This class handles cache operations and determines the project root automatically.
    """
    
    def __init__(self, cache_name):
        """
        Initialize the cache manager
        
        Args:
            cache_name (str): Identifier for the cache file
        """
        self.cache_name = cache_name
        self._project_root = self._find_project_root()
    
    def _find_project_root(self):
        """
        Find the project root directory by looking for marker files
        
        Returns:
            Path: The path to the project root
        """
        # Start with the current file's directory
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        
        # In Docker, the app directory is likely /app
        if os.path.exists('/app'):
            return Path('/app')
            
        # If we're in the app subdirectory, go up one level
        if current_dir.name == 'app':
            return current_dir.parent
            
        # Walk up the directory tree until we find a marker file
        search_dir = current_dir
        while search_dir:
            # Check for common project root markers
            if (search_dir / '.git').exists() or \
               (search_dir / 'pyproject.toml').exists() or \
               (search_dir / 'setup.py').exists() or \
               (search_dir / 'requirements.txt').exists() or \
               (search_dir / 'Dockerfile').exists():
                logger.debug(f"Found project root at: {search_dir}")
                return search_dir
            
            # Move up one directory
            parent_dir = search_dir.parent
            if parent_dir == search_dir:  # Reached filesystem root
                break
            search_dir = parent_dir
        
        # If no project root markers found, use one level up from the current directory
        # since we're likely in app/
        if current_dir.name == 'app':
            return current_dir.parent
            
        # Last resort: use the current directory
        logger.debug(f"No project root markers found, using current directory: {current_dir}")
        return current_dir
    
    def _get_cache_dir(self):
        """Get or create the cache directory in the project root"""
        cache_dir = self._project_root / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def _get_cache_file(self):
        """Get the path to the cache file"""
        return self._get_cache_dir() / f"{self.cache_name}.json"
    
    def save(self, data):
        """
        Save data to a local cache file
        
        Args:
            data: Data to save (must be JSON serializable)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cache_file = self._get_cache_file()
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Data saved to cache: {self.cache_name} at {cache_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving data to cache {self.cache_name}: {e}")
            return False
    
    
    def _get_cache_file(self):
        """Get the path to the cache file"""
        return self._get_cache_dir() / f"{self.cache_name}.json"
    
    
    def load(self):
        """
        Load data from a local cache file
        
        Returns:
            Data from cache, or None if not found or error
        """
        try:
            cache_file = self._get_cache_file()
            if not cache_file.exists():
                logger.debug(f"No cache file found: {self.cache_name}")
                return None
            
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            logger.debug(f"Data loaded from cache: {self.cache_name}")
            return cached_data
            
        except Exception as e:
            logger.error(f"Error loading data from cache {self.cache_name}: {e}")
            return None
    
    def clear(self):
        """
        Clear the cache
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cache_file = self._get_cache_file()
            if cache_file.exists():
                with open(cache_file, 'w') as f:
                    json.dump({}, f)  # Empty JSON object
                logger.debug(f"Cache cleared: {self.cache_name}")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache {self.cache_name}: {e}")
            return False
    
    def delete(self):
        """
        Delete the cache file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cache_file = self._get_cache_file()
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Cache file deleted: {self.cache_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cache file {self.cache_name}: {e}")
            return False