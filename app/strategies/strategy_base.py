from abc import ABC, abstractmethod
from typing import List

from app.models.strategy import TradingResult
from app.utils.binance.client import KlineData


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
    def generate_trading_signals(self, klines: List[KlineData]) -> TradingResult:
        """
        Process historical data and generate trading signals.
        
        Args:
            klines: List of KlineData objects containing historical price/volume data
            
        Returns:
            A dictionary containing:
                - 'data': The processed data with indicators
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
