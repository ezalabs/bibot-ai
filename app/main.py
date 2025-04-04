from binance.client import Client
from binance.enums import (
    SIDE_BUY,
    SIDE_SELL,
    ORDER_TYPE_MARKET,
    FUTURE_ORDER_TYPE_STOP_MARKET,
    FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET
)
import pandas as pd
import ta
import time
import signal
import sys
from cache_manager import CacheManager
from logger import get_logger
import config
from binance.exceptions import BinanceAPIException
import requests.exceptions

# Configure logging
logger = get_logger()

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    """Handle shutdown signals by saving state before exit"""
    logger.info("Shutdown signal received, saving state...")
    if 'bot' in globals() and hasattr(bot, '_save_positions_to_cache'):
        bot._save_positions_to_cache()
    logger.info("State saved, exiting")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Handle termination signal

class BiBot:
    def __init__(self):
        logger.info("Initializing BiBot ...")
        self.client = None
        self._initialize_client()
        
        # Set leverage
        try:
            self.client.futures_change_leverage(
                symbol=config.TRADING_PAIR,
                leverage=config.LEVERAGE
            )
            logger.info(f"Set leverage to {config.LEVERAGE}x for {config.TRADING_PAIR}")
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            raise
        
        # Initialize cache manager for positions
        self.positions_cache = CacheManager(f"positions_{config.TRADING_PAIR}")
        
        # Initialize trading state
        self.active_positions = []
        self.last_trade_time = 0
        self.min_trade_interval = 60  # Minimum seconds between trades
        
        # Load active positions from cache
        self._load_positions_from_cache()
        
        logger.info("BiBot initialization completed")

    def _initialize_client(self, max_retries=3, retry_delay=5):
        """Initialize the Binance client with retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to Binance {'Testnet' if config.USE_TESTNET else 'Mainnet'} (Attempt {attempt + 1} / {max_retries})")
                self.client = Client(
                    config.API_KEY, 
                    config.API_SECRET, 
                    testnet=config.USE_TESTNET
                )
                # Test the connection
                self.client.ping()
                logger.info(f"Successfully connected to Binance {'Testnet' if config.USE_TESTNET else 'Mainnet'}")
                return
            except (BinanceAPIException, requests.exceptions.RequestException) as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to Binance after maximum retries")
                    raise Exception("Could not connect to Binance API.")

    def _load_positions_from_cache(self):
        """Load active positions from cache and validate them"""
        cached_positions = self.positions_cache.load()
        
        if cached_positions is None:
            logger.info("No positions found in cache")
            return
            
        if not isinstance(cached_positions, list):
            logger.warning("Invalid cache format for positions, expected a list")
            return
            
        valid_positions = []
        for position in cached_positions:
            # Validate position structure
            if all(key in position for key in ['main_order_id', 'entry_price', 'side', 'quantity', 'orders']):
                valid_positions.append(position)
            else:
                logger.warning(f"Skipped invalid position from cache: {position}")
        
        self.active_positions = valid_positions
        logger.info(f"Loaded {len(valid_positions)} valid positions from cache")
        
        # Check for closed positions right after loading
        if valid_positions:
            logger.info("Checking status of cached positions...")
            self.check_closed_positions()
            
    def _save_positions_to_cache(self):
        """Save current active positions to cache"""
        result = self.positions_cache.save(self.active_positions)
        if not result:
            logger.warning("Failed to save positions to cache")
        else:
            logger.debug(f"Saved {len(self.active_positions)} positions to cache")

    def get_historical_data(self):
        """Fetch historical klines/candlestick data"""
        logger.debug(f"Fetching historical data for {config.TRADING_PAIR}")
        try:
            klines = self.client.futures_klines(
                symbol=config.TRADING_PAIR,
                interval=Client.KLINE_INTERVAL_1MINUTE,
                limit=100
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert string values to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            logger.debug(f"Latest price: {df['close'].iloc[-1]}")
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise

    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        logger.debug("Calculating technical indicators...")
        try:
            # RSI
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=config.RSI_PERIOD).rsi()
            logger.debug(f"Current RSI: {df['rsi'].iloc[-1]:.2f}")
            
            # EMAs
            df['ema_fast'] = ta.trend.EMAIndicator(df['close'], window=config.EMA_FAST).ema_indicator()
            df['ema_slow'] = ta.trend.EMAIndicator(df['close'], window=config.EMA_SLOW).ema_indicator()
            logger.debug(f"Current EMAs - Fast: {df['ema_fast'].iloc[-1]:.2f}, Slow: {df['ema_slow'].iloc[-1]:.2f}")
            
            return df
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            raise

    def check_entry_conditions(self, df):
        """Check if entry conditions are met"""
        logger.debug("Checking entry conditions...")
        try:
            last_row = df.iloc[-1]
            
            # RSI conditions
            rsi_oversold = last_row['rsi'] < config.RSI_OVERSOLD
            rsi_overbought = last_row['rsi'] > config.RSI_OVERBOUGHT
            logger.debug(f"RSI: {last_row['rsi']:.2f} (Oversold: {rsi_oversold}, Overbought: {rsi_overbought})")
            
            # EMA crossover
            ema_cross_up = (df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and
                          df['ema_fast'].iloc[-2] <= df['ema_slow'].iloc[-2])
            ema_cross_down = (df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1] and
                            df['ema_fast'].iloc[-2] >= df['ema_slow'].iloc[-2])
            logger.debug(f"EMA Crossover - Up: {ema_cross_up}, Down: {ema_cross_down}")
            
            conditions = {
                'long': rsi_oversold and ema_cross_up,
                'short': rsi_overbought and ema_cross_down
            }
            logger.debug(f"Entry conditions - Long: {conditions['long']}, Short: {conditions['short']}")
            return conditions
        except Exception as e:
            logger.error(f"Error checking entry conditions: {e}")
            raise

    def place_order(self, side, quantity):
        """Place a futures order with associated stop loss and take profit orders"""
        logger.info(f"Placing {side} order for {quantity} {config.TRADING_PAIR}")
        try:
            # Place main order
            order = self.client.futures_create_order(
                symbol=config.TRADING_PAIR,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
                newOrderRespType="RESULT"
            )
            logger.info(f"Main order placed successfully at {order['avgPrice']}")
            
            # Get order ID and position side
            order_id = order['orderId']
            position_side = side
            close_side = SIDE_SELL if side == SIDE_BUY else SIDE_BUY
            
            # Calculate stop loss and take profit prices
            entry_price = float(order['avgPrice'])
            stop_loss = round(entry_price * (1 - config.STOP_LOSS_PERCENTAGE / 100) 
                              if side == SIDE_BUY else entry_price * (1 + config.STOP_LOSS_PERCENTAGE / 100), 1)
            take_profit = round(entry_price * (1 + config.TAKE_PROFIT_PERCENTAGE / 100) 
                                if side == SIDE_BUY else entry_price * (1 - config.TAKE_PROFIT_PERCENTAGE / 100), 1)
            
            logger.info(f"Setting stop loss at {stop_loss:.2f} and take profit at {take_profit:.2f}")
            
            # Store all orders for this position
            position_info = {
                'main_order_id': order_id,
                'entry_price': entry_price,
                'side': position_side,
                'quantity': quantity,
                'orders': []  # Will store related order IDs
            }
            
            # Place stop loss order
            sl_order = self.client.futures_create_order(
                symbol=config.TRADING_PAIR,
                side=close_side,
                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                stopPrice=stop_loss,
                quantity=quantity,
                reduceOnly=True,  # Important: ensures this only reduces the position
                closePosition=False  # Not closing entire position if partial
            )
            logger.info(f"Stop loss order placed successfully: ID {sl_order['orderId']}")
            position_info['orders'].append({'type': 'stop_loss', 'id': sl_order['orderId']})
            
            # Place take profit order
            tp_order = self.client.futures_create_order(
                symbol=config.TRADING_PAIR,
                side=close_side,
                type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                stopPrice=take_profit,
                quantity=quantity,
                reduceOnly=True,  # Important: ensures this only reduces the position
                closePosition=False  # Not closing entire position if partial
            )
            logger.info(f"Take profit order placed successfully: ID {tp_order['orderId']}")
            position_info['orders'].append({'type': 'take_profit', 'id': tp_order['orderId']})
            
            # Add to active positions list
            self.active_positions.append(position_info)
            
            # Save updated positions to cache
            self._save_positions_to_cache()
            
            return position_info
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def check_closed_positions(self):
        """Check for positions that have been closed and clean up related orders"""
        positions_to_remove = []
        
        for i, position in enumerate(self.active_positions):
            # Check if position is still open
            position_info = self.client.futures_position_information(symbol=config.TRADING_PAIR)
            position_closed = True  # Assume closed until proven open
            
            for p in position_info:
                if p['symbol'] == config.TRADING_PAIR and float(p['positionAmt']) != 0:
                    position_closed = False
                    break
            
            if position_closed:
                # Cancel any remaining orders for this position
                for order_info in position['orders']:
                    try:
                        self.client.futures_cancel_order(
                            symbol=config.TRADING_PAIR,
                            orderId=order_info['id']
                        )
                        logger.info(f"Cancelled order {order_info['id']} for closed position")
                    except:
                        logger.info(f"Order {order_info['id']} already executed or cancelled")
                
                positions_to_remove.append(i)
        
        # Remove closed positions from the tracking list
        for index in sorted(positions_to_remove, reverse=True):
            logger.info(f"Removing closed position from tracking: {self.active_positions[index]}")
            self.active_positions.pop(index)
        
        # If any positions were removed, update the cache
        if positions_to_remove:
            self._save_positions_to_cache()

    def cleanup_all_positions(self):
        """Force cleanup of all tracked positions"""
        logger.info("Performing cleanup of all tracked positions...")
        
        # Get all open orders
        open_orders = self.client.futures_get_open_orders(symbol=config.TRADING_PAIR)
        order_ids = [order['orderId'] for order in open_orders]
        
        # Try to cancel each order
        for position in self.active_positions:
            for order_info in position['orders']:
                order_id = order_info['id']
                if order_id in order_ids:
                    try:
                        self.client.futures_cancel_order(
                            symbol=config.TRADING_PAIR,
                            orderId=order_id
                        )
                        logger.info(f"Cancelled order {order_id}")
                    except Exception as e:
                        logger.warning(f"Could not cancel order {order_id}: {e}")
        
        # Clear active positions list
        self.active_positions = []
        
        # Clear the cache
        self.positions_cache.clear()
        
        logger.info("Cleanup completed, all positions have been cleared from tracking")

    def run(self):
        """Main bot loop"""
        logger.info(f"Starting BiBot for {config.TRADING_PAIR}")
        logger.info(f"Configuration - Leverage: {config.LEVERAGE}x, Position Size: {config.POSITION_SIZE}, Max Positions: {config.MAX_POSITIONS}")
        
        check_positions_interval = 30  # Check for closed positions every 30 seconds
        last_check_time = 0
        
        while True:
            try:
                current_time = time.time()
                
                # Periodically check for closed positions
                if current_time - last_check_time > check_positions_interval:
                    logger.debug("Checking for closed positions...")
                    self.check_closed_positions()
                    last_check_time = current_time
                
                # Check if we can open new positions
                if len(self.active_positions) >= config.MAX_POSITIONS:
                    logger.info("Maximum positions reached, waiting...")
                    time.sleep(10)  # Sleep for a shorter time to check positions more frequently
                    continue
                
                # Get historical data and calculate indicators
                df = self.get_historical_data()
                df = self.calculate_indicators(df)
                
                # Check entry conditions
                conditions = self.check_entry_conditions(df)
                
                if current_time - self.last_trade_time < self.min_trade_interval:
                    logger.debug("Waiting for minimum trade interval...")
                    time.sleep(1)
                    continue
                
                # Execute trades based on conditions
                if conditions['long']:
                    logger.info("Long entry conditions met, placing order...")
                    order = self.place_order(SIDE_BUY, config.POSITION_SIZE)
                    if order:
                        logger.info(f"Long position opened at {order['entry_price']}")
                        self.last_trade_time = current_time
                
                elif conditions['short']:
                    logger.info("Short entry conditions met, placing order...")
                    order = self.place_order(SIDE_SELL, config.POSITION_SIZE)
                    if order:
                        logger.info(f"Short position opened at {order['entry_price']}")
                        self.last_trade_time = current_time
                
                time.sleep(1)  # Wait 1 second before next iteration
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                logger.info("Waiting 60 seconds before retrying...")
                time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='BiBot - Binance Futures Trading Bot')
    parser.add_argument('--cleanup', action='store_true', help='Clean up all tracked positions and exit')
    args = parser.parse_args()
    
    bot = BiBot()
    
    if args.cleanup:
        bot.cleanup_all_positions()
        logger.info("Cleanup completed, exiting")
        sys.exit(0)
    
    bot.run()