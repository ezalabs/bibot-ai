from typing import Optional, Dict, Any
from datetime import datetime

from app.config.settings import BiBotConfig, load_config
from app.registry import ServiceRegistry
from app.utils.logging.logger import get_logger


logger = get_logger(__name__)

class TradingExecutor:
    """
    TradingExecutor - Focused on executing trades and managing positions.
    """
    
    def __init__(self, service_registry: Optional[ServiceRegistry] = None, config: Optional[BiBotConfig] = None):
        """
        Initialize the trading executor
        
        Args:
            service_registry: Service registry to use (created if not provided)
            config: Configuration object (used if service_registry not provided)
        """
        self.config = config or load_config()
        self.services = service_registry or ServiceRegistry(self.config)
        
        logger.info("TradingExecutor initialized successfully")
    
    def generate_trading_signals(self, interval: str = None):
        """
        Generate trading signals using the configured strategy
        
        Args:
            interval: Optional timeframe interval (e.g., '1m', '5m')
            
        Returns:
            Dictionary containing the trading signals and additional data
        """
        # Get market data with optional interval override
        df = self.services.market_data.get_historical_data(interval=interval)
        
        # Generate signals
        return self.services.strategy.generate_trading_signals(df)
    
    def cleanup_all_positions(self) -> None:
        """Clean up all tracked positions"""
        logger.info("Cleaning up all positions...")
        
        # Loop through all positions and clean them up
        positions = self.services.position_manager.active_positions.copy()
        for position in positions:
            self.services.position_manager.cleanup_position(position)
        
        logger.info("Position cleanup completed")
    
    def get_account_info(self) -> dict:
        """
        Get account information including balance, positions, and margin data
        
        Returns:
            Dictionary with account information
        """
        try:
            # Get account balances
            balance_info = self.services.client.get_account_balance()
            
            # Get current positions
            positions = self.services.position_manager.active_positions
            position_info = [{
                "id": p.main_order_id,
                "side": p.side,
                "entry_price": p.entry_price,
                "quantity": p.quantity,
                "created_at": p.timestamp.isoformat() if p.timestamp else None
            } for p in positions]
            
            return {
                "balance": balance_info,
                "active_positions": position_info,
                "position_count": len(positions),
                "max_positions": self.config.trading.max_positions
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"error": str(e)}

    def execute_long_trade(self, position_size: Optional[float] = None) -> Dict[str, Any]:
        """Execute a long trade with the specified position size"""
        if position_size is None:
            position_size = self.config.trading.position_size
        
        try:
            # Check position limit
            pm = self.services.position_manager
            current_positions = pm.get_position_count()
            max_positions = self.config.trading.max_positions
            if pm.has_reached_position_limit():
                return {
                    "success": False,
                    "error": "Maximum position limit reached",
                    "limit_info": {
                        "current_positions": current_positions,
                        "max_positions": max_positions,
                        "limit_reached": True
                    }
                }
            
            # Execute the trade
            position = self.services.order_manager.open_long_position(position_size)
            
            if position:
                # Add position to manager
                self.services.position_manager.add_position(position)
                
                return {
                    "success": True,
                    "position": {
                        "id": position.main_order_id,
                        "side": position.side,
                        "entry_price": position.entry_price,
                        "quantity": position.quantity,
                        "timestamp": position.timestamp.isoformat() if position.timestamp else datetime.now().isoformat(),
                        "orders": [{"type": o.type, "id": o.id} for o in position.orders]
                    },
                    "message": f"Long position opened at {position.entry_price}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to open long position",
                    "message": "Order execution failed, check logs for details"
                }
            
        except Exception as e:
            logger.error(f"Error executing long trade: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Exception occurred during trade execution"
            }

    def execute_short_trade(self, position_size: Optional[float] = None) -> Dict[str, Any]:
        """Execute a short trade with the specified position size"""
        if position_size is None:
            position_size = self.config.trading.position_size
        
        try:
            # Check position limit
            pm = self.services.position_manager
            current_positions = pm.get_position_count()
            max_positions = self.config.trading.max_positions
            if pm.has_reached_position_limit():
                return {
                    "success": False,
                    "error": "Maximum position limit reached",
                    "limit_info": {
                        "current_positions": current_positions,
                        "max_positions": max_positions,
                        "limit_reached": True
                    }
                }
            
            # Execute the trade
            position = self.services.order_manager.open_short_position(position_size)
            
            if position:
                # Add position to manager
                self.services.position_manager.add_position(position)
                
                return {
                    "success": True,
                    "position": {
                        "id": position.main_order_id,
                        "side": position.side,
                        "entry_price": position.entry_price,
                        "quantity": position.quantity,
                        "timestamp": position.timestamp.isoformat() if position.timestamp else datetime.now().isoformat(),
                        "orders": [{"type": o.type, "id": o.id} for o in position.orders]
                    },
                    "message": f"Short position opened at {position.entry_price}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to open short position",
                    "message": "Order execution failed, check logs for details"
                }
            
        except Exception as e:
            logger.error(f"Error executing short trade: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Exception occurred during trade execution"
            }
