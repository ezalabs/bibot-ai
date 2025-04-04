from abc import ABC, abstractmethod

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
    def generate_trading_signals(self, df):
        """
        Process historical data and generate trading signals.
        
        Args:
            df (pandas.DataFrame): Raw historical price/volume data
            
        Returns:
            dict: A dictionary containing:
                 - 'data': The DataFrame with added indicators (optional)
                 - 'signals': A dictionary with at least 'long' and 'short' boolean keys
        """
        pass
    
    def get_name(self):
        """
        Get the name of the strategy.
        
        Returns:
            str: The name of the strategy
        """
        return self.__class__.__name__
