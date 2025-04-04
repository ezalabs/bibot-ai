from typing import Dict, Type
from app.config.settings import load_config, BiBotConfig
from app.strategies.strategy_base import TradingStrategy
from app.strategies.implementations.rsi_ema_strategy import RsiEmaStrategy
from app.utils.logging.logger import get_logger

logger = get_logger()

class StrategyFactory:
    """Factory class for creating trading strategy instances"""
    
    # Registry of available strategies
    _strategies: Dict[str, Type[TradingStrategy]] = {
        "RSI_EMA": RsiEmaStrategy,
        # Add new strategies here as they are implemented
    }
    
    @classmethod
    def create_strategy(cls, strategy_name: str = None, config: BiBotConfig = None) -> TradingStrategy:
        """
        Create a strategy instance based on name or config
        
        Args:
            strategy_name: Name of the strategy to create (overrides config if provided)
            config: Configuration object containing strategy selection
            
        Returns:
            An instance of the requested trading strategy
        """
        
        config = config or load_config()
            
        # Use provided strategy name or get from config
        strategy_key = strategy_name or config.strategy
        
        # Get strategy class from registry
        strategy_class = cls._strategies.get(strategy_key)
        
        if not strategy_class:
            logger.warning(f"Strategy '{strategy_key}' not found, defaulting to RSI_EMA")
            strategy_class = RsiEmaStrategy
            
        # Create and return strategy instance
        return strategy_class()
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[TradingStrategy]) -> None:
        """
        Register a new strategy class
        
        Args:
            name: Name to register the strategy under
            strategy_class: The strategy class to register
        """
        cls._strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name}")
