from typing import Dict, Type, Optional
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
    def create_strategy(
        cls,
        strategy_name: Optional[str] = None,
        config: Optional[BiBotConfig] = None
    ) -> TradingStrategy:
        """
        Create a strategy instance
        
        Args:
            strategy_name: Name of the strategy to create. If None, uses default from config
            config: Configuration object. Required for strategy initialization
            
        Returns:
            Instance of the requested strategy
            
        Raises:
            ValueError: If strategy_name is not found in registry
        """
        if strategy_name is None:
            if config is None:
                raise ValueError("config is required when strategy_name is not provided")
            strategy_name = config.strategy
        
        if strategy_name not in cls._strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found in registry")
            
        strategy_class = cls._strategies[strategy_name]
        return strategy_class(config=config)
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[TradingStrategy]) -> None:
        """
        Register a new strategy with the factory
        
        Args:
            name: Name to register the strategy under
            strategy_class: Strategy class to register
        """
        cls._strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name}")
