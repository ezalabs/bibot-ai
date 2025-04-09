from typing import List
from datetime import datetime
import json

from app.config.settings import BiBotConfig
from app.models.position import Position
from app.utils.binance.client import BinanceClient
from app.utils.storage.cache_manager import CacheManager
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)

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
            
            # Verify positions are still valid after loading
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
            # Convert to dict for serialization
            position_data = [p.model_dump(mode='json') for p in self.active_positions]
            result = self.cache.save(position_data)
            
            if result:
                logger.debug(f"Saved {len(self.active_positions)} positions to cache")
            else:
                logger.warning("Failed to save positions to cache")
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
    
    def check_closed_positions(self) -> None:
        """Check for positions that have been closed based on API position status and order status, then cleanup."""
        if not self.active_positions:
            return # No positions being tracked
        
        try:
            # Get data from Binance API
            open_orders = self.client.get_open_orders(self.config.trading.trading_pair)
            open_order_ids = {order.orderId for order in open_orders} 
            
            current_binance_positions = self.client.get_positions(self.config.trading.trading_pair)
            # Create a set of symbols that have an actual open position on Binance
            open_position_symbols = {p.symbol for p in current_binance_positions if float(p.positionAmt) != 0}
            
            positions_to_remove = []
            positions_kept = []
            
            # Check each locally tracked position
            for position in self.active_positions:
                symbol = self.config.trading.trading_pair # Assuming all positions managed are for the configured pair
                
                # Condition 1: Does the position still exist on Binance?
                position_exists_on_binance = symbol in open_position_symbols
                
                # Condition 2: Does the position have any associated SL/TP orders still open?
                associated_orders_open = False
                for order_info in position.orders:
                    if order_info.id in open_order_ids:
                        associated_orders_open = True
                        break 
                
                # Determine if the position should be considered closed
                is_closed = False
                if not position_exists_on_binance:
                    logger.info(f"Position {position.main_order_id} ({position.side}) no longer exists on Binance API. Marking as closed.")
                    is_closed = True
                elif not associated_orders_open:
                    # Position might exist, but if our SL/TP orders are gone, we consider it closed for cleanup
                    logger.info(f"Position {position.main_order_id} ({position.side}) exists on Binance but has no associated open SL/TP orders. Marking as closed for cleanup.")
                    is_closed = True
                    
                # Process closed or kept positions
                if is_closed:
                    # Attempt to cancel the orders associated with this closed position just in case
                    logger.debug(f"Attempting to cancel orders for closed position {position.main_order_id}")
                    cancelled_count = 0
                    for order_info in position.orders:
                        try:
                            # Use the stored order ID for cancellation
                            self.client.cancel_order(symbol, order_info.id)
                            logger.info(f"Successfully cancelled lingering order {order_info.id} for closed position {position.main_order_id}")
                            cancelled_count += 1
                        except Exception as e:
                            # Ignore errors if order is already gone
                            if "Unknown order" not in str(e):
                                 logger.warning(f"Failed to cancel lingering order {order_info.id} for position {position.main_order_id}: {e}")
                    logger.debug(f"Cancelled {cancelled_count} lingering orders for position {position.main_order_id}.")        
                    positions_to_remove.append(position)
                else:
                    # Keep tracking this position
                    positions_kept.append(position)
            
            # Update the active positions list if any were marked for removal
            if positions_to_remove:
                self.active_positions = positions_kept
                self._save_positions()
                logger.info(f"Removed {len(positions_to_remove)} closed position(s) and attempted cleanup.")
                
        except Exception as e:
            logger.error(f"Error checking closed positions: {e}")
    
    def _cleanup_all_positions(self) -> None:
        """Clean up all positions and cancel remaining orders - USE WITH CAUTION"""
        logger.warning("Executing cleanup of ALL tracked positions and associated open orders.")
        # Get open orders
        try:
            open_orders = self.client.get_open_orders(self.config.trading.trading_pair)
            
            # Cancel all orders found for the pair
            cancelled_count = 0
            for order in open_orders:
                # Optional: Check if the order belongs to any tracked position before cancelling?
                # Currently cancels ALL open orders for the pair.
                try:
                    self.client.cancel_order(self.config.trading.trading_pair, order.orderId)
                    logger.info(f"Cancelled order {order.orderId}")
                    cancelled_count += 1
                except Exception as e:
                    # Log error but continue trying to cancel others
                    logger.warning(f"Failed to cancel order {order.orderId}: {e}")
            
            logger.info(f"Attempted to cancel {len(open_orders)} open order(s), {cancelled_count} successful.")

        except Exception as e:
             logger.error(f"Error fetching open orders during cleanup: {e}")

        # Clear all tracked positions locally and save
        cleared_count = len(self.active_positions)
        self.active_positions = []
        self._save_positions()
        logger.info(f"Cleared {cleared_count} locally tracked positions.")
    
    def cleanup_position(self, position: Position) -> bool:
        """
        Clean up a specific position by cancelling its associated orders.
        
        Args:
            position: Position to clean up
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Cleaning up specific position {position.main_order_id}")
        
        # Cancel only the associated orders for this specific position
        success = True
        cancelled_count = 0
        for order_info in position.orders:
            try:
                self.client.cancel_order(self.config.trading.trading_pair, order_info.id)
                logger.info(f"Successfully cancelled order {order_info.id} for position {position.main_order_id}")
                cancelled_count += 1
            except Exception as e:
                # Log error but continue trying to cancel others for this position
                 # Ignore errors (e.g., order already cancelled/filled - error code -2011)
                if "Unknown order" not in str(e):
                    logger.warning(f"Failed to cancel order {order_info.id} for position {position.main_order_id}: {e}")
                success = False # Mark as unsuccessful if any order fails, except for 'Unknown order'
        
        # Remove from active positions list
        initial_count = len(self.active_positions)
        self.active_positions = [p for p in self.active_positions 
                              if p.main_order_id != position.main_order_id]
        removed = initial_count > len(self.active_positions)
        
        if removed:
             logger.info(f"Removed position {position.main_order_id} from tracking.")
             self._save_positions()
        else:
            logger.warning(f"Position {position.main_order_id} not found in active list during cleanup.")

        logger.info(f"Cleanup for position {position.main_order_id} finished. Cancelled {cancelled_count} orders.")
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
