from typing import Dict, Any, Optional
from datetime import datetime

from app.config.settings import load_config
from app.registry import ServiceRegistry
from app.utils.logging.logger import get_logger
from app.core.trading_executor import TradingExecutor

logger = get_logger(__name__)

class ExecutionTool:
    """Tool for executing trades and managing positions."""
    
    def __init__(self, trading_executor=None, config=None):
        """
        Initialize the execution tool.
        
        Args:
            trading_executor: TradingExecutor to use (created if not provided)
            config: Config for creating trading_executor if needed
        """
        self.config = config or load_config()
        self.trading_executor = trading_executor or TradingExecutor(config=self.config)
    
    def check_position_limit(self) -> Dict[str, Any]:
        """Check if position limit is reached"""
        try:
            pm = self.trading_executor.services.position_manager
            current_positions = pm.get_position_count()
            max_positions = self.config.trading.max_positions
            limit_reached = pm.has_reached_position_limit()
            
            return {
                "current_positions": current_positions,
                "max_positions": max_positions,
                "limit_reached": limit_reached,
                "can_open_position": not limit_reached
            }
        except Exception as e:
            logger.error(f"Error checking position limit: {e}")
            raise
    
    def execute_long_trade(self, position_size: Optional[float] = None) -> Dict[str, Any]:
        """Execute long trade - delegate to TradingExecutor"""
        return self.trading_executor.execute_long_trade(position_size)
    
    def execute_short_trade(self, position_size: Optional[float] = None) -> Dict[str, Any]:
        """Execute short trade - delegate to TradingExecutor"""
        return self.trading_executor.execute_short_trade(position_size)
    
    def get_active_positions(self) -> Dict[str, Any]:
        """Get active positions"""
        return self.trading_executor.get_account_info() 