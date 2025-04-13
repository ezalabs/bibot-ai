from binance.client import Client
from binance.enums import (
    SIDE_BUY,
    SIDE_SELL,
    ORDER_TYPE_MARKET,
    FUTURE_ORDER_TYPE_STOP_MARKET,
    FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET
)
from typing import Optional
from datetime import datetime
from app.config.settings import BiBotConfig
from app.models.position import Position, OrderInfo
from app.utils.logging.logger import get_logger
from app.utils.binance.client import BinanceClient

logger = get_logger(__name__)

class OrderManager:
    """Manages order placement and position tracking"""
    
    def __init__(self, client: BinanceClient, config: BiBotConfig):
        """
        Initialize the order manager
        
        Args:
            client: Initialized Binance client wrapper
            config: Application configuration
        """
        self.client = client
        self.config = config
    
    def place_market_order(self, side: str, quantity: float) -> Optional[Position]:
        """
        Place a market order with stop loss and take profit
        
        Args:
            side: Order side (BUY or SELL)
            quantity: Order quantity
            
        Returns:
            Position object if successful, None otherwise
        """
        trading_pair = self.config.trading.trading_pair
        logger.info(f"Placing {side} order for {quantity} {trading_pair}")
        
        try:
            # Place main order using the client wrapper method
            order = self.client.place_market_order(
                symbol=trading_pair,
                side=side,
                quantity=quantity
            )
            
            # Get order details
            order_id = order.orderId
            entry_price = float(order.avgPrice)
            close_side = SIDE_SELL if side == SIDE_BUY else SIDE_BUY
            
            # Calculate SL/TP levels
            sl_price, tp_price = self._calculate_sl_tp_levels(side, entry_price)
            
            # Create the position object
            position = Position(
                main_order_id=str(order_id),
                entry_price=entry_price,
                side=side,
                quantity=quantity,
                orders=[],
                timestamp=datetime.now()
            )
            
            # Add stop loss
            sl_order = self._place_stop_loss(trading_pair, close_side, sl_price, quantity)
            if sl_order:
                position.orders.append(OrderInfo(type='stop_loss', id=str(sl_order.orderId)))
            
            # Add take profit
            tp_order = self._place_take_profit(trading_pair, close_side, tp_price, quantity)
            if tp_order:
                position.orders.append(OrderInfo(type='take_profit', id=str(tp_order.orderId)))
            
            return position
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def _calculate_sl_tp_levels(self, side: str, entry_price: float) -> tuple[float, float]:
        """Calculate stop loss and take profit price levels"""
        if side == SIDE_BUY:
            # Long position
            sl_price = round(entry_price * (1 - self.config.trading.stop_loss_percentage / 100), 1)
            tp_price = round(entry_price * (1 + self.config.trading.take_profit_percentage / 100), 1)
        else:
            # Short position
            sl_price = round(entry_price * (1 + self.config.trading.stop_loss_percentage / 100), 1)
            tp_price = round(entry_price * (1 - self.config.trading.take_profit_percentage / 100), 1)
        
        return sl_price, tp_price
    
    def _place_stop_loss(self, symbol: str, side: str, price: float, quantity: float):
        """Place a stop loss order"""
        try:
            # Use client wrapper method
            order = self.client.place_stop_loss_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=price
            )
            logger.info(f"Stop loss order placed at {price}")
            return order
        except Exception as e:
            logger.error(f"Failed to place stop loss: {e}")
            return None
    
    def _place_take_profit(self, symbol: str, side: str, price: float, quantity: float):
        """Place a take profit order"""
        try:
            # Use client wrapper method
            order = self.client.place_take_profit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=price
            )
            logger.info(f"Take profit order placed at {price}")
            return order
        except Exception as e:
            logger.error(f"Failed to place take profit: {e}")
            return None
    
    def open_long_position(self, quantity: float) -> Optional[Position]:
        """
        Open a long position (buy) with stop loss and take profit
        
        Args:
            quantity: Order quantity
            
        Returns:
            Position object if successful, None otherwise
        """
        return self.place_market_order(SIDE_BUY, quantity)
    
    def open_short_position(self, quantity: float) -> Optional[Position]:
        """
        Open a short position (sell) with stop loss and take profit
        
        Args:
            quantity: Order quantity
            
        Returns:
            Position object if successful, None otherwise
        """
        return self.place_market_order(SIDE_SELL, quantity)
