from typing import Dict, List, Any
import pandas as pd
from datetime import datetime

from app.config.settings import BiBotConfig
from app.utils.binance.client import BinanceClient, KlineData
from app.utils.logging.logger import get_logger

logger = get_logger()

class MarketData:
    """
    Handles market data retrieval and processing
    """
    
    def __init__(self, client: BinanceClient, config: BiBotConfig):
        """
        Initialize the market data handler
        
        Args:
            client: Binance client wrapper
            config: Application configuration
        """
        self.client = client
        self.config = config
        self.symbol = config.trading.trading_pair
        
        # Cache for historical data
        self._klines_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self._last_update: Dict[str, Dict[str, datetime]] = {}
        self._cache_expiry = 60  # seconds
    
    def get_historical_data(
        self, 
        interval: str = '1m',
        limit: int = 100,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get historical klines/candlestick data
        
        Args:
            interval: Kline interval (1m, 5m, etc.)
            limit: Number of klines to retrieve
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with historical price data
        """
        # Check if we have valid cached data
        current_time = datetime.now()
        cache_key = f"{self.symbol}_{interval}"
        
        if use_cache and cache_key in self._klines_cache:
            last_update = self._last_update.get(cache_key, {}).get('klines')
            if last_update and (current_time - last_update).total_seconds() < self._cache_expiry:
                logger.debug(f"Using cached klines data for {cache_key}")
                return self._klines_cache[cache_key]
        
        # Fetch new data
        logger.debug(f"Fetching {limit} klines for {self.symbol} at {interval} interval")
        try:
            klines = self.client.get_klines(
                symbol=self.symbol,
                interval=interval,
                limit=limit
            )
            
            # Convert to DataFrame
            df = self._convert_klines_to_dataframe(klines)
            
            # Cache the result
            self._klines_cache[cache_key] = df
            if cache_key not in self._last_update:
                self._last_update[cache_key] = {}
            self._last_update[cache_key]['klines'] = current_time
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise
    
    def _convert_klines_to_dataframe(self, klines: List[KlineData]) -> pd.DataFrame:
        """
        Convert raw klines data to pandas DataFrame
        
        Args:
            klines: List of kline data from Binance API
            
        Returns:
            DataFrame with properly formatted columns
        """
        df = pd.DataFrame(klines)
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Set datetime as index
        df.set_index('datetime', inplace=True)
        
        # Sort by time ascending
        df.sort_index(inplace=True)
        
        return df
    
    def get_current_price(self) -> float:
        """
        Get current price for the configured symbol
        
        Returns:
            Current price as float
        """
        try:
            # Use the latest kline close price
            df = self.get_historical_data(limit=1)
            return df['close'].iloc[-1]
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            raise
    
    def get_price_change_24h(self) -> float:
        """
        Get 24-hour price change percentage
        
        Returns:
            Percentage change as float
        """
        try:
            # Get 24h of data
            df = self.get_historical_data(interval='1h', limit=24)
            first_price = df['close'].iloc[0]
            last_price = df['close'].iloc[-1]
            
            change_percent = ((last_price - first_price) / first_price) * 100
            return change_percent
        except Exception as e:
            logger.error(f"Error calculating 24h price change: {e}")
            raise
    
    def get_volume_24h(self) -> float:
        """
        Get 24-hour trading volume
        
        Returns:
            24-hour volume
        """
        try:
            df = self.get_historical_data(interval='1h', limit=24)
            return df['volume'].sum()
        except Exception as e:
            logger.error(f"Error calculating 24h volume: {e}")
            raise
    
    def get_order_book_summary(self, limit: int = 5) -> Dict[str, Any]:
        """
        Get order book summary with best bid/ask and book imbalance
        
        Args:
            limit: Number of levels to retrieve
            
        Returns:
            Dictionary with order book summary
        """
        try:
            # Not implemented in the client wrapper yet
            # This would require adding a method to BinanceClient
            return {
                "not_implemented": True
            }
        except Exception as e:
            logger.error(f"Error getting order book: {e}")
            raise
