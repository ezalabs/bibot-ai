from typing import Dict, Any, Optional
import pandas as pd

from app.config.settings import BiBotConfig, load_config
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)

class RiskTool:
    """Tool for risk assessment and position sizing."""
    
    def __init__(self, config: BiBotConfig = None):
        """Initialize the risk tool."""
        self.config = config or load_config()
    
    def calculate_position_size(self, market_data: Dict[str, Any], risk_percentage: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate optimal position size based on risk parameters.
        
        Args:
            market_data: Dictionary containing market data
            risk_percentage: Percentage of capital to risk (optional)
            
        Returns:
            Dictionary with position sizing recommendation
        """
        try:
            # Get the trading parameters from config
            position_size = self.config.trading.position_size
            stop_loss_pct = self.config.trading.stop_loss_percentage
            leverage = self.config.trading.leverage
            
            # Get market data
            raw_data = market_data.get("raw_data", {})
            market_summary = market_data.get("market_summary", {})
            
            # Get current price
            current_price = market_summary.get("current_price")
            if not current_price and isinstance(raw_data, dict):
                # Try to get it from raw data
                df = pd.DataFrame(raw_data)
                if not df.empty and 'close' in df:
                    current_price = df['close'].iloc[-1]
            
            if not current_price:
                return {
                    "error": "Unable to determine current price",
                    "recommended_position_size": position_size,
                    "is_default": True
                }
            
            # Calculate volatility (as a simple measure of risk)
            volatility = None
            if isinstance(raw_data, dict):
                df = pd.DataFrame(raw_data)
                if not df.empty and 'close' in df:
                    volatility = df['close'].pct_change().std() * 100
            
            # If we couldn't calculate volatility, use default
            if volatility is None:
                return {
                    "recommended_position_size": position_size,
                    "leverage": leverage,
                    "is_default": True,
                    "risk_percentage": risk_percentage or (stop_loss_pct / 100)
                }
            
            # Dynamic position sizing based on volatility
            # Higher volatility = smaller position size
            volatility_factor = 1.0
            if volatility > 2.0:
                volatility_factor = 0.8  # Reduce size by 20% for high volatility
            elif volatility > 1.5:
                volatility_factor = 0.9  # Reduce size by 10% for medium volatility
            elif volatility < 0.5:
                volatility_factor = 1.1  # Increase size by 10% for low volatility
            
            # Calculate recommended position size
            recommended_size = position_size * volatility_factor
            
            # Round to appropriate decimal places based on price
            if current_price > 1000:
                recommended_size = round(recommended_size, 5)
            elif current_price > 100:
                recommended_size = round(recommended_size, 4)
            elif current_price > 10:
                recommended_size = round(recommended_size, 3)
            elif current_price > 1:
                recommended_size = round(recommended_size, 2)
            else:
                recommended_size = round(recommended_size, 1)
            
            return {
                "recommended_position_size": recommended_size,
                "base_position_size": position_size,
                "volatility": volatility,
                "volatility_factor": volatility_factor,
                "leverage": leverage,
                "is_default": False,
                "risk_percentage": risk_percentage or (stop_loss_pct / 100)
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                "error": str(e),
                "recommended_position_size": self.config.trading.position_size,
                "is_default": True
            }
    
    def calculate_stop_loss_levels(self, market_data: Dict[str, Any], side: str) -> Dict[str, Any]:
        """
        Calculate optimal stop loss and take profit levels.
        
        Args:
            market_data: Dictionary containing market data
            side: Trade side ('BUY' or 'SELL')
            
        Returns:
            Dictionary with stop loss and take profit recommendations
        """
        try:
            # Get default SL/TP percentages from config
            sl_pct = self.config.trading.stop_loss_percentage
            tp_pct = self.config.trading.take_profit_percentage
            
            # Get market data
            raw_data = market_data.get("raw_data", {})
            market_summary = market_data.get("market_summary", {})
            
            # Get current price
            current_price = market_summary.get("current_price")
            if not current_price and isinstance(raw_data, dict):
                # Try to get it from raw data
                df = pd.DataFrame(raw_data)
                if not df.empty and 'close' in df:
                    current_price = df['close'].iloc[-1]
            
            if not current_price:
                return {
                    "error": "Unable to determine current price",
                    "stop_loss_percentage": sl_pct,
                    "take_profit_percentage": tp_pct,
                    "is_default": True
                }
            
            # Convert DataFrame if needed for analysis
            df = None
            if isinstance(raw_data, dict):
                df = pd.DataFrame(raw_data)
            
            # Dynamic SL/TP based on volatility
            volatility = None
            if df is not None and not df.empty and 'close' in df:
                volatility = df['close'].pct_change().std() * 100
            
            # If we couldn't calculate volatility, use default
            if volatility is None:
                # Calculate default SL/TP levels
                if side.upper() == 'BUY':
                    sl_price = round(current_price * (1 - sl_pct / 100), 1)
                    tp_price = round(current_price * (1 + tp_pct / 100), 1)
                else:
                    sl_price = round(current_price * (1 + sl_pct / 100), 1)
                    tp_price = round(current_price * (1 - tp_pct / 100), 1)
                    
                return {
                    "stop_loss_percentage": sl_pct,
                    "take_profit_percentage": tp_pct,
                    "stop_loss_price": sl_price,
                    "take_profit_price": tp_price,
                    "is_default": True
                }
            
            # Adjust SL/TP based on volatility
            # Higher volatility = wider SL/TP to avoid premature stop outs
            volatility_factor = 1.0
            if volatility > 2.0:
                volatility_factor = 1.2  # Increase SL/TP by 20% for high volatility
            elif volatility > 1.5:
                volatility_factor = 1.1  # Increase SL/TP by 10% for medium volatility
            
            # Calculate adjusted SL/TP percentages
            adjusted_sl_pct = sl_pct * volatility_factor
            adjusted_tp_pct = tp_pct * volatility_factor
            
            # Calculate SL/TP prices
            if side.upper() == 'BUY':
                sl_price = round(current_price * (1 - adjusted_sl_pct / 100), 1)
                tp_price = round(current_price * (1 + adjusted_tp_pct / 100), 1)
            else:
                sl_price = round(current_price * (1 + adjusted_sl_pct / 100), 1)
                tp_price = round(current_price * (1 - adjusted_tp_pct / 100), 1)
            
            return {
                "original_stop_loss_percentage": sl_pct,
                "original_take_profit_percentage": tp_pct,
                "adjusted_stop_loss_percentage": adjusted_sl_pct,
                "adjusted_take_profit_percentage": adjusted_tp_pct,
                "stop_loss_price": sl_price,
                "take_profit_price": tp_price,
                "current_price": current_price,
                "volatility": volatility,
                "volatility_factor": volatility_factor,
                "is_default": False
            }
            
        except Exception as e:
            logger.error(f"Error calculating stop loss levels: {e}")
            return {
                "error": str(e),
                "stop_loss_percentage": sl_pct,
                "take_profit_percentage": tp_pct,
                "is_default": True
            }
    
    def perform_risk_assessment(self, market_data: Dict[str, Any], trading_signals: Dict[str, bool]) -> Dict[str, Any]:
        """
        Perform comprehensive risk assessment for potential trades.
        
        Args:
            market_data: Dictionary containing market data
            trading_signals: Dictionary containing trading signals
            
        Returns:
            Dictionary with risk assessment results
        """
        try:
            # Determine trade side from signals
            side = "BUY" if trading_signals.get("long", False) else "SELL" if trading_signals.get("short", False) else None
            
            # If no signals, return a default assessment
            if not side:
                return {
                    "trade_opportunity": False,
                    "message": "No trading signals present",
                    "risk_level": "none"
                }
                
            # Calculate position size
            position_size_data = self.calculate_position_size(market_data)
            
            # Calculate SL/TP levels
            sl_tp_data = self.calculate_stop_loss_levels(market_data, side)
            
            # Get market data for additional analysis
            # TODO: Add additional analysis
            market_summary = market_data.get("market_summary", {})
            
            # Get volatility
            volatility = sl_tp_data.get("volatility")
            
            # Determine risk level
            risk_level = "medium"  # Default
            if volatility:
                if volatility > 2.0:
                    risk_level = "high"
                elif volatility < 1.0:
                    risk_level = "low"
            
            # Risk-to-reward ratio
            risk_reward_ratio = sl_tp_data.get("adjusted_take_profit_percentage", 0) / sl_tp_data.get("adjusted_stop_loss_percentage", 1)
            
            # Determine if trade is favorable
            favorable_trade = risk_reward_ratio >= 1.5 and risk_level != "high"
            
            return {
                "trade_opportunity": True,
                "side": side,
                "risk_level": risk_level,
                "volatility": volatility,
                "risk_reward_ratio": round(risk_reward_ratio, 2),
                "favorable_trade": favorable_trade,
                "position_sizing": position_size_data,
                "stop_loss_take_profit": sl_tp_data,
                "recommendation": "Execute trade" if favorable_trade else "Consider alternatives due to risk profile"
            }
            
        except Exception as e:
            logger.error(f"Error performing risk assessment: {e}")
            return {
                "error": str(e),
                "trade_opportunity": False,
                "risk_level": "unknown",
                "message": "Error during risk assessment"
            } 