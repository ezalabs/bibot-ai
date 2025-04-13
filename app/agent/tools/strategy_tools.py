from typing import Dict, Any, List
import pandas as pd

from app.config.settings import TradingConfig, load_config
from app.registry import ServiceRegistry
from app.utils.logging.logger import get_logger
from app.core.trading_executor import TradingExecutor

logger = get_logger(__name__)

class StrategyTool:
    """Tool for strategy selection and signal generation."""
    
    def __init__(self, service_registry=None, config = None):
        """
        Initialize the strategy tool.
        
        Args:
            service_registry: Service registry to use (created if not provided)
            config: Config to use if creating a new ServiceRegistry
        """
        self.config = config or load_config()

        self.services = service_registry or ServiceRegistry(self.config)
        self.rsi_ema_strategy = service_registry.strategy
        
        # Strategy registry
        self.strategies = {
            "rsi_ema": self.generate_rsi_ema_signals,
            # Add more strategies as they are implemented
        }
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """
        Get list of available trading strategies.
        
        Returns:
            List of strategy information dictionaries
        """
        strategies = [
            {
                "id": "rsi_ema",
                "name": "RSI + EMA Strategy",
                "description": "Uses RSI for momentum and EMA for trend direction",
                "parameters": {
                    "rsi_period": self.config.rsi_ema.rsi_period,
                    "rsi_overbought": self.config.rsi_ema.rsi_overbought,
                    "rsi_oversold": self.config.rsi_ema.rsi_oversold,
                    "ema_fast": self.config.rsi_ema.ema_fast,
                    "ema_slow": self.config.rsi_ema.ema_slow
                }
            }
            # Will add more strategies here as they are implemented
        ]
        
        return strategies
    
    def evaluate_strategy_suitability(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate which strategy is most suitable for current market conditions.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary with strategy recommendations and reasons
        """
        try:
            raw_data = market_data.get("raw_data", {})
            market_summary = market_data.get("market_summary", {})
            
            # Convert raw_data back to DataFrame if it's a dict
            df = pd.DataFrame(raw_data) if isinstance(raw_data, dict) else raw_data
            
            # Get volatility (if available)
            volatility = market_summary.get("volatility", None)
            if volatility is None and not df.empty:
                volatility = df['close'].pct_change().std() * 100
            
            # Simple logic for strategy selection
            if volatility and volatility > 2.0:
                # High volatility market
                strategy_id = "rsi_ema"
                reason = "Market showing high volatility, RSI+EMA strategy suitable for capturing reversals"
            else:
                # Default to RSI+EMA for now
                strategy_id = "rsi_ema"
                reason = "RSI+EMA strategy is versatile for current market conditions"
                
            return {
                "recommended_strategy": strategy_id,
                "reason": reason,
                "all_strategies": self.get_available_strategies()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating strategy suitability: {e}")
            
            # Default to RSI+EMA in case of error
            return {
                "recommended_strategy": "rsi_ema",
                "reason": "Default strategy selected due to evaluation error",
                "all_strategies": self.get_available_strategies(),
                "error": str(e)
            }
    
    def generate_signals(self, strategy_id: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signals using the specified strategy.
        
        Args:
            strategy_id: ID of the strategy to use
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary with trading signals and analysis
        """
        try:
            # Get the strategy function from the registry
            strategy_func = self.strategies.get(strategy_id)
            
            if not strategy_func:
                raise ValueError(f"Strategy '{strategy_id}' not found")
                
            # Call the appropriate strategy function
            return strategy_func(market_data)
            
        except Exception as e:
            logger.error(f"Error generating signals with strategy {strategy_id}: {e}")
            raise
    
    def generate_rsi_ema_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate signals using the RSI+EMA strategy.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary with trading signals and analysis
        """
        try:
            # Get raw data
            raw_data = market_data.get("raw_data", {})
            
            # Convert raw data to a proper format for the strategy
            if isinstance(raw_data, dict):
                # If raw_data is a dict (converted from DataFrame), convert it back to DataFrame
                df = pd.DataFrame(raw_data)
                
                # Create a list of mock KlineData structures from the DataFrame
                klines = []
                for _, row in df.iterrows():
                    kline = {
                        'timestamp': row.get('timestamp', 0),
                        'open': row.get('open', 0.0),
                        'high': row.get('high', 0.0),
                        'low': row.get('low', 0.0),
                        'close': row.get('close', 0.0),
                        'volume': row.get('volume', 0.0),
                        'quote_volume': row.get('quote_volume', 0.0),
                        'trades': row.get('trades', 0),
                        'taker_buy_base': row.get('taker_buy_base', 0.0),
                        'taker_buy_quote': row.get('taker_buy_quote', 0.0)
                    }
                    klines.append(kline)
                
                # Now use the list of klines with the strategy
                result = self.rsi_ema_strategy.generate_trading_signals(klines)
            elif isinstance(raw_data, pd.DataFrame):
                # If it's already a DataFrame, convert to klines
                klines = []
                for timestamp, row in raw_data.iterrows():
                    kline = {
                        'timestamp': int(timestamp.timestamp() * 1000) if hasattr(timestamp, 'timestamp') else 0,
                        'open': row.get('open', 0.0),
                        'high': row.get('high', 0.0),
                        'low': row.get('low', 0.0),
                        'close': row.get('close', 0.0),
                        'volume': row.get('volume', 0.0),
                        'quote_volume': row.get('quote_volume', 0.0) if 'quote_volume' in row else 0.0,
                        'trades': row.get('trades', 0) if 'trades' in row else 0,
                        'taker_buy_base': row.get('taker_buy_base', 0.0) if 'taker_buy_base' in row else 0.0,
                        'taker_buy_quote': row.get('taker_buy_quote', 0.0) if 'taker_buy_quote' in row else 0.0
                    }
                    klines.append(kline)
                
                result = self.rsi_ema_strategy.generate_trading_signals(klines)
            else:
                # If it's already a list of KlineData objects
                klines = raw_data
                result = self.rsi_ema_strategy.generate_trading_signals(klines)
            
            # Extract signals and data
            signals = result.get("signals", {"long": False, "short": False})
            data = result.get("data", pd.DataFrame())
            
            # Get the latest indicator values
            latest_data = {}
            if not data.empty:
                latest_data = {
                    "rsi": data["rsi"].iloc[-1] if "rsi" in data else None,
                    "ema_fast": data["ema_fast"].iloc[-1] if "ema_fast" in data else None,
                    "ema_slow": data["ema_slow"].iloc[-1] if "ema_slow" in data else None,
                    "rsi_change": data["rsi_change"].iloc[-1] if "rsi_change" in data else None,
                    "ema_fast_slope": data["ema_fast_slope"].iloc[-1] if "ema_fast_slope" in data else None,
                    "ema_slow_slope": data["ema_slow_slope"].iloc[-1] if "ema_slow_slope" in data else None
                }
            
            return {
                "strategy": "rsi_ema",
                "signals": signals,
                "latest_data": latest_data,
                "parameters": {
                    "rsi_period": self.config.rsi_ema.rsi_period,
                    "rsi_overbought": self.config.rsi_ema.rsi_overbought,
                    "rsi_oversold": self.config.rsi_ema.rsi_oversold,
                    "ema_fast": self.config.rsi_ema.ema_fast,
                    "ema_slow": self.config.rsi_ema.ema_slow
                }
            }
                
        except Exception as e:
            logger.error(f"Error generating RSI+EMA signals: {e}")
            return {
                "strategy": "rsi_ema",
                "signals": {"long": False, "short": False},
                "error": str(e)
            } 