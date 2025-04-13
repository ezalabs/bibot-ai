import time
from typing import Any, Dict, List, Optional, TypeVar, Callable, TypedDict
import functools

from binance.client import Client
from binance.exceptions import BinanceAPIException
import requests.exceptions

from app.config.settings import BiBotConfig
from app.models.binance import BinanceOrder, BinancePosition
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)

# Type for the decorator's return function
T = TypeVar('T')

class KlineData(TypedDict):
    """Type definition for kline/candlestick data"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_volume: float
    trades: int
    taker_buy_base: float
    taker_buy_quote: float
    ignore: float

def retry(
    max_retries: int = 3,
    retry_delay: int = 1,
    backoff_factor: float = 2.0,
    allowed_exceptions: tuple = (BinanceAPIException, requests.exceptions.RequestException),
):
    """
    Decorator for retrying API calls with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        allowed_exceptions: Exceptions that trigger a retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = retry_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    # Don't retry on certain error codes
                    if isinstance(e, BinanceAPIException):
                        # API key errors, invalid parameters, etc. won't be resolved by retrying
                        if e.code in (-2014, -2015, -1021, -1022):
                            logger.error(f"Non-retriable Binance error: {e}")
                            raise
                    
                    last_exception = e
                    wait_time = delay * (backoff_factor ** attempt)
                    
                    logger.warning(
                        f"API call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time:.1f}s"
                    )
                    
                    time.sleep(wait_time)
            
            # If we get here, all retries failed
            logger.error(f"All {max_retries} retry attempts failed.")
            if last_exception:
                raise last_exception
            
            # This shouldn't happen but is needed for type checking
            raise RuntimeError("Unexpected error in retry mechanism")
            
        return wrapper
    return decorator

class BinanceClient:
    """
    Enhanced Binance client with better error handling and type safety
    """
    
    def __init__(self, config: BiBotConfig):
        """
        Initialize the Binance client wrapper
        
        Args:
            config: Application configuration containing API credentials
        """
        self.config = config
        self._client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the underlying Binance client"""
        try:
            logger.info(f"Initializing Binance {'Testnet' if self.config.trading.use_testnet else 'Mainnet'} client")
            self._client = Client(
                self.config.credentials.api_key,
                self.config.credentials.api_secret,
                testnet=self.config.trading.use_testnet
            )
            # Test connection
            self._client.ping()
            logger.info("Successfully connected to Binance API")
            
            # Set leverage according to configuration
            try:
                trading_pair = self.config.trading.trading_pair
                leverage = self.config.trading.leverage
                self._client.futures_change_leverage(
                    symbol=trading_pair,
                    leverage=leverage
                )
                logger.info(f"Set leverage to {leverage}x for {trading_pair}")
            except Exception as e:
                logger.error(f"Failed to set leverage: {e}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
    
    @property
    def client(self) -> Client:
        """Get the underlying Binance client"""
        if not self._client:
            self._initialize_client()
        return self._client
    
    @retry(max_retries=3)
    def ping(self) -> Dict[str, Any]:
        """Test connectivity to the Binance API"""
        return self.client.ping()
    
    @retry(max_retries=3)
    def get_klines(
        self, 
        symbol: str,
        interval: str = Client.KLINE_INTERVAL_1MINUTE,
        limit: int = 100
    ) -> List[KlineData]:
        """
        Get klines/candlestick data
        
        Args:
            symbol: The trading pair
            interval: Kline interval (1m, 5m, etc.)
            limit: Number of klines to retrieve
            
        Returns:
            List of kline data
        """
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Convert to properly typed dictionary
            result = []
            for k in klines:
                kline_data: KlineData = {
                    'timestamp': int(k[0]),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': int(k[6]),
                    'quote_volume': float(k[7]),
                    'trades': int(k[8]),
                    'taker_buy_base': float(k[9]),
                    'taker_buy_quote': float(k[10]),
                    'ignore': float(k[11])
                }
                result.append(kline_data)
                
            return result
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            raise
    
    @retry(max_retries=3)
    def place_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> BinanceOrder:
        """
        Place a market order
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            
        Returns:
            Order information
        """
        try:
            response = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=quantity,
                newOrderRespType="RESULT"
            )
            # Convert to Pydantic model for validation
            try:
                return BinanceOrder.model_validate(response)
            except Exception as e:
                logger.error(f"Error validating order response: {e}")
                # Create a manual conversion as fallback
                return BinanceOrder(
                    orderId=str(response.get('orderId', '')),
                    symbol=str(response.get('symbol', '')),
                    status=str(response.get('status', '')),
                    clientOrderId=str(response.get('clientOrderId', '')),
                    price=str(response.get('price', '0')),
                    avgPrice=str(response.get('avgPrice', '0')),
                    origQty=str(response.get('origQty', '0')),
                    executedQty=str(response.get('executedQty', '0')),
                    type=str(response.get('type', '')),
                    side=str(response.get('side', ''))
                )
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            raise
    
    @retry(max_retries=3)
    def place_stop_loss_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        stop_price: float
    ) -> BinanceOrder:
        """
        Place a stop loss order
        
        Args:
            symbol: Trading pair
            side: BUY or SELL (opposite of position side)
            quantity: Order quantity
            stop_price: Stop trigger price
            
        Returns:
            Order information
        """
        try:
            response = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=Client.FUTURE_ORDER_TYPE_STOP_MARKET,
                quantity=quantity,
                stopPrice=stop_price,
                reduceOnly=True,
                closePosition=False
            )
            try:
                return BinanceOrder.model_validate(response)
            except Exception as e:
                logger.error(f"Error validating stop loss order response: {e}")
                # Create a manual conversion as fallback
                return BinanceOrder(
                    orderId=str(response.get('orderId', '')),
                    symbol=str(response.get('symbol', '')),
                    status=str(response.get('status', '')),
                    clientOrderId=str(response.get('clientOrderId', '')),
                    price=str(response.get('price', '0')),
                    avgPrice=str(response.get('avgPrice', '0')),
                    origQty=str(response.get('origQty', '0')),
                    executedQty=str(response.get('executedQty', '0')),
                    type=str(response.get('type', '')),
                    side=str(response.get('side', ''))
                )
        except Exception as e:
            logger.error(f"Error placing stop loss order: {e}")
            raise
    
    @retry(max_retries=3)
    def place_take_profit_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        stop_price: float
    ) -> BinanceOrder:
        """
        Place a take profit order
        
        Args:
            symbol: Trading pair
            side: BUY or SELL (opposite of position side)
            quantity: Order quantity
            stop_price: Take profit trigger price
            
        Returns:
            Order information
        """
        try:
            response = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=Client.FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                quantity=quantity,
                stopPrice=stop_price,
                reduceOnly=True,
                closePosition=False
            )
            try:
                return BinanceOrder.model_validate(response)
            except Exception as e:
                logger.error(f"Error validating take profit order response: {e}")
                # Create a manual conversion as fallback
                return BinanceOrder(
                    orderId=str(response.get('orderId', '')),
                    symbol=str(response.get('symbol', '')),
                    status=str(response.get('status', '')),
                    clientOrderId=str(response.get('clientOrderId', '')),
                    price=str(response.get('price', '0')),
                    avgPrice=str(response.get('avgPrice', '0')),
                    origQty=str(response.get('origQty', '0')),
                    executedQty=str(response.get('executedQty', '0')),
                    type=str(response.get('type', '')),
                    side=str(response.get('side', ''))
                )
        except Exception as e:
            logger.error(f"Error placing take profit order: {e}")
            raise
    
    @retry(max_retries=3)
    def get_positions(self, symbol: Optional[str] = None) -> List[BinancePosition]:
        """
        Get current positions
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of position information
        """
        try:
            response = self.client.futures_position_information(symbol=symbol)
            result = []
            
            for pos in response:
                try:
                    result.append(BinancePosition.model_validate(pos))
                except Exception as e:
                    logger.error(f"Error validating position: {e}")
                    # Create manual conversion as fallback
                    result.append(BinancePosition(
                        symbol=str(pos.get('symbol', '')),
                        positionAmt=str(pos.get('positionAmt', '0')),
                        entryPrice=str(pos.get('entryPrice', '0')),
                        markPrice=str(pos.get('markPrice', '0')),
                        unRealizedProfit=str(pos.get('unRealizedProfit', '0')),
                        liquidationPrice=str(pos.get('liquidationPrice', '0')),
                        leverage=str(pos.get('leverage', '1')),
                        marginType=str(pos.get('marginType', '')),
                        isolatedMargin=str(pos.get('isolatedMargin', '0')),
                        positionSide=str(pos.get('positionSide', ''))
                    ))
            
            return result
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise
    
    @retry(max_retries=3)
    def get_open_orders(self, symbol: Optional[str] = None) -> List[BinanceOrder]:
        """
        Get all open orders
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of open orders
        """
        try:
            response = self.client.futures_get_open_orders(symbol=symbol)
            result = []
            
            for order in response:
                try:
                    result.append(BinanceOrder.model_validate(order))
                except Exception as e:
                    logger.error(f"Error validating order in get_open_orders: {e}")
                    # Manually create the order
                    result.append(BinanceOrder(
                        orderId=str(order.get('orderId', '')),
                        symbol=str(order.get('symbol', '')),
                        status=str(order.get('status', '')),
                        clientOrderId=str(order.get('clientOrderId', '')),
                        price=str(order.get('price', '0')),
                        avgPrice=str(order.get('avgPrice', '0')),
                        origQty=str(order.get('origQty', '0')),
                        executedQty=str(order.get('executedQty', '0')),
                        type=str(order.get('type', '')),
                        side=str(order.get('side', ''))
                    ))
            
            return result
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            raise
    
    @retry(max_retries=3)
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            symbol: Trading pair
            order_id: ID of the order to cancel
            
        Returns:
            Cancellation response
        """
        try:
            return self.client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )
        except BinanceAPIException as e:
            # Order may already be executed/canceled
            if e.code == -2011:  # Unknown order
                logger.info(f"Order {order_id} already executed or cancelled")
                return {"status": "CANCELED", "orderId": order_id}
            raise
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            raise
    
    @retry(max_retries=3)
    def change_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Change leverage for a symbol
        
        Args:
            symbol: Trading pair
            leverage: Leverage value (1-125)
            
        Returns:
            Leverage update response
        """
        try:
            return self.client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
        except Exception as e:
            logger.error(f"Error changing leverage for {symbol}: {e}")
            raise
