from typing import List
from datetime import datetime
import json

from app.config.settings import BiBotConfig
from app.models.position import Position
from app.utils.binance.client import BinanceClient
from app.utils.storage.cache_manager import CacheManager
from app.utils.logging.logger import get_logger

logger = get_logger()

class PositionManager:
    """
    Manages trading positions, including tracking, storage, and lifecycle
    """
    
    def __init__(self, client: BinanceClient, config: BiBotConfig):
        """
        Initialize the position manager
        
        Args:
            client: Binance client
            config: Application configuration
        """
        self.client = client
        self.config = config
        self.active_positions: List[Position] = []
        
        # Initialize cache for position storage
        self.cache = CacheManager(f"positions_{config.trading.trading_pair}")
    
    def add_position(self, position: Position) -> None:
        """
        Add a new position to the tracking list
        
        Args:
            position: Position to add
        """
        logger.info(f"Adding new position: {position.side} at {position.entry_price}")
        self.active_positions.append(position)
        self._save_positions()
    
    def load_positions(self) -> None:
        """Load positions from cache"""
        try:
            cached_data = self.cache.load()
            if not cached_data:
                logger.info("No cached positions found")
                return
            
            if not isinstance(cached_data, list):
                logger.warning("Invalid position cache format - expected list")
                return
            
            valid_positions: List[Position] = []
            for position_data in cached_data:
                try:
                    # Convert dictionary to Position model
                    position = Position.model_validate(position_data)
                    valid_positions.append(position)
                except Exception as e:
                    logger.warning(f"Skipped invalid position: {e}")
            
            self.active_positions = valid_positions
            logger.info(f"Loaded {len(valid_positions)} positions from cache")
            
            # Verify positions are still valid
            if valid_positions:
                self.check_closed_positions()
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing position cache: {e}")
            logger.info("Clearing invalid position cache")
            self.clear_cache()
        except Exception as e:
            logger.error(f"Unexpected error loading positions: {e}")
            logger.info("Clearing position cache due to error")
            self.clear_cache()
    
    def _save_positions(self) -> None:
        """Save positions to cache"""
        try:
            # Convert to dict for serialization, handling datetime
            position_data = []
            for p in self.active_positions:
                pos_dict = p.model_dump()
                # Convert datetime to string for JSON serialization
                if isinstance(pos_dict['timestamp'], datetime):
                    pos_dict['timestamp'] = pos_dict['timestamp'].isoformat()
                position_data.append(pos_dict)
            
            result = self.cache.save(position_data)
            
            if result:
                logger.debug(f"Saved {len(self.active_positions)} positions to cache")
            else:
                logger.warning("Failed to save positions to cache")
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
    
    def check_closed_positions(self) -> None:
        """Check for positions that have been closed and clean up"""
        if not self.active_positions:
            return
        
        # Get current positions from Binance
        current_positions = self.client.get_positions(self.config.trading.trading_pair)
        
        # Check if we have an open position
        has_open_position = False
        for pos in current_positions:
            if pos.symbol == self.config.trading.trading_pair and float(pos.positionAmt) != 0:
                has_open_position = True
                break
        
        if not has_open_position:
            # No open positions, so all tracked positions should be removed
            logger.info("No open positions found, cleaning up all tracked positions")
            self._cleanup_all_positions()
            return
        
        # Process open orders to determine which positions are closed
        open_orders = self.client.get_open_orders(self.config.trading.trading_pair)
        open_order_ids = [order.orderId for order in open_orders]
        
        positions_to_remove = []
        
        # Check each position
        for i, position in enumerate(self.active_positions):
            # Check if any orders for this position are still open
            position_has_open_orders = False
            for order in position.orders:
                if order.id in open_order_ids:
                    position_has_open_orders = True
                    break
            
            if not position_has_open_orders:
                # All orders closed or executed, position is closed
                logger.info(f"Position {position.main_order_id} no longer has open orders, marking as closed")
                positions_to_remove.append(i)
        
        # Remove closed positions
        for index in sorted(positions_to_remove, reverse=True):
            logger.info(f"Removing closed position: {self.active_positions[index].main_order_id}")
            self.active_positions.pop(index)
        
        if positions_to_remove:
            self._save_positions()
    
    def _cleanup_all_positions(self) -> None:
        """Clean up all positions and cancel remaining orders"""
        # Get open orders
        open_orders = self.client.get_open_orders(self.config.trading.trading_pair)
        
        # Cancel all orders
        for order in open_orders:
            try:
                self.client.cancel_order(self.config.trading.trading_pair, order.orderId)
                logger.info(f"Cancelled order {order.orderId}")
            except Exception as e:
                logger.warning(f"Failed to cancel order {order.orderId}: {e}")
        
        # Clear all tracked positions
        self.active_positions = []
        self._save_positions()
        logger.info("All positions cleaned up")
    
    def cleanup_position(self, position: Position) -> bool:
        """
        Clean up a specific position
        
        Args:
            position: Position to clean up
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Cleaning up position {position.main_order_id}")
        
        # Cancel all associated orders
        success = True
        for order_info in position.orders:
            try:
                self.client.cancel_order(self.config.trading.trading_pair, order_info.id)
                logger.info(f"Cancelled order {order_info.id}")
            except Exception as e:
                logger.warning(f"Failed to cancel order {order_info.id}: {e}")
                success = False
        
        # Remove from active positions
        self.active_positions = [p for p in self.active_positions 
                              if p.main_order_id != position.main_order_id]
        self._save_positions()
        
        return success
    
    def get_position_count(self) -> int:
        """Get number of active positions"""
        return len(self.active_positions)
    
    def has_reached_position_limit(self) -> bool:
        """Check if maximum position count has been reached"""
        return self.get_position_count() >= self.config.trading.max_positions
    
    def clear_cache(self) -> None:
        """Clear the position cache"""
        self.cache.clear()
        logger.info("Position cache cleared")
