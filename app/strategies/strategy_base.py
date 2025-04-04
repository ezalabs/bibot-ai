from abc import ABC, abstractmethod
import pandas as pd

from app.models.strategy import TradingResult


class TradingStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Concrete strategy implementations should inherit from this class
    and implement the required methods.
    """
    
    def __init__(self):
        """
        Initialize the strategy.
        """
        pass
    
    @abstractmethod
    def generate_trading_signals(self, df: pd.DataFrame) -> TradingResult:
        """
        Process historical data and generate trading signals.
        
        Args:
            df: Raw historical price/volume data
            
        Returns:
            A dictionary containing:
                - 'data': The DataFrame with added indicators
                - 'signals': A dictionary with 'long' and 'short' boolean keys
        """
        pass
    
    def get_name(self) -> str:
        """
        Get the name of the strategy.
        
        Returns:
            The name of the strategy
        """
        return self.__class__.__name__
