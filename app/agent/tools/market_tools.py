from typing import Dict, Any
import pandas as pd
from datetime import datetime

from app.config.settings import load_config
from app.registry import ServiceRegistry
from app.utils.data_converter import convert_klines_to_dataframe
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)

class MarketDataTool:
    """Tool for fetching and analyzing market data."""
    
    def __init__(self, service_registry=None, market_data=None, config=None):
        """
        Initialize the market data tool.
        
        Args:
            service_registry: Service registry to use
            market_data: Directly injected market_data service (highest priority)
            config: Config to use if creating a new registry
        """
        self.config = config or load_config()
        
        # Use directly provided market_data if available
        if market_data:
            self.market_data = market_data
            self.services = None
        else:
            # Otherwise use or create a service registry
            self.services = service_registry or ServiceRegistry(self.config)
            self.market_data = self.services.market_data
            
        # Reference to client for potential direct usage
        self.client = (
            self.services.client if self.services 
            else None  # If market_data was directly injected
        )
    
    def get_market_data(self, interval: str = '1m', limit: int = 100) -> Dict[str, Any]:
        """
        Fetch market data and perform basic analysis.
        
        Args:
            interval: Kline interval (1m, 5m, etc.)
            limit: Number of klines to retrieve
            
        Returns:
            Dictionary containing market data and basic analysis
        """
        try:
            # Get historical data using BiBot's market_data service
            klines = self.market_data.get_historical_data(interval=interval, limit=limit)
            
            # Convert to dataframe
            df = convert_klines_to_dataframe(klines)
            
            # Get current price (last close)
            current_price = df['close'].iloc[-1]
            
            # Calculate basic price stats
            price_change_24h = self._calculate_price_change(df)
            price_high_24h = df['high'].max()
            price_low_24h = df['low'].min()
            
            # Calculate volume metrics
            volume_data = self._analyze_volume(df)
            
            # Get market summary
            market_summary = {
                "trading_pair": self.config.trading.trading_pair,
                "current_price": current_price,
                "price_change_24h": price_change_24h,
                "price_high_24h": price_high_24h,
                "price_low_24h": price_low_24h,
                "volume_data": volume_data,
                "timestamp": datetime.now().isoformat(),
            }
            
            return {
                "raw_data": df.tail(20).to_dict(),  # Send just the last 20 rows to keep state size manageable
                "market_summary": market_summary
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            raise
    
    def _calculate_price_change(self, df: pd.DataFrame) -> float:
        """Calculate 24-hour price change percentage."""
        if len(df) < 2:
            return 0.0
        
        first_price = df['open'].iloc[0]
        last_price = df['close'].iloc[-1]
        
        if first_price == 0:
            return 0.0
            
        return ((last_price - first_price) / first_price) * 100
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trading volume patterns."""
        if len(df) < 2:
            return {"avg_volume": 0.0}
        
        avg_volume = df['volume'].mean()
        max_volume = df['volume'].max()
        volume_trend = "increasing" if df['volume'].iloc[-1] > avg_volume else "decreasing"
        
        return {
            "avg_volume": avg_volume,
            "max_volume": max_volume,
            "volume_trend": volume_trend
        }
        
    def analyze_market_sentiment(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze market sentiment based on price action and volume.
        This is a simple implementation that could be enhanced with actual
        sentiment data from news sources or social media.
        """
        # Simple sentiment analysis based on price and volume trends
        price_trend = "bullish" if df['close'].iloc[-1] > df['close'].iloc[-10:].mean() else "bearish"
        
        # Check if volume is increasing or decreasing
        volume_trend = "high" if df['volume'].iloc[-1] > df['volume'].iloc[-10:].mean() else "low"
        
        # Calculate price volatility
        volatility = df['close'].pct_change().std() * 100
        
        # Determine overall sentiment
        if price_trend == "bullish" and volume_trend == "high":
            overall_sentiment = "strongly_bullish"
        elif price_trend == "bullish" and volume_trend == "low":
            overall_sentiment = "mildly_bullish"
        elif price_trend == "bearish" and volume_trend == "high":
            overall_sentiment = "strongly_bearish"
        else:
            overall_sentiment = "mildly_bearish"
            
        return {
            "price_trend": price_trend,
            "volume_trend": volume_trend,
            "volatility": volatility,
            "overall_sentiment": overall_sentiment
        } 