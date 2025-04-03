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
import config
import logging
from binance.exceptions import BinanceAPIException
import requests.exceptions

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
        
        # Initialize trading state
        self.active_positions = []
        self.last_trade_time = 0
        self.min_trade_interval = 60  # Minimum seconds between trades
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
                logger.error(f"Connection attempt {attempt + 1} failed. Status code {str(e.status_code)}")
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to Binance after maximum retries")
                    raise Exception("Could not connect to Binance API.")

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
        """Place a futures order"""
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
            
            # Calculate stop loss and take profit prices
            entry_price = float(order['avgPrice'])
            stop_loss = round(entry_price * (1 - config.STOP_LOSS_PERCENTAGE / 100) 
                              if side == SIDE_BUY else entry_price * (1 + config.STOP_LOSS_PERCENTAGE / 100), 1)
            take_profit = round(entry_price * (1 + config.TAKE_PROFIT_PERCENTAGE / 100) 
                                if side == SIDE_BUY else entry_price * (1 - config.TAKE_PROFIT_PERCENTAGE / 100), 1)
            
            logger.info(f"Setting stop loss at {stop_loss:.2f} and take profit at {take_profit:.2f}")
            
            # Place stop loss order
            self.client.futures_create_order(
                symbol=config.TRADING_PAIR,
                side=SIDE_SELL if side == SIDE_BUY else SIDE_BUY,
                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                stopPrice=stop_loss,
                quantity=quantity
            )
            logger.info("Stop loss order placed successfully")
            
            # Place take profit order
            self.client.futures_create_order(
                symbol=config.TRADING_PAIR,
                side=SIDE_SELL if side == SIDE_BUY else SIDE_BUY,
                type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                stopPrice=take_profit,
                quantity=quantity
            )
            logger.info("Take profit order placed successfully")
            
            return order
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def run(self):
        """Main bot loop"""
        logger.info(f"Starting BiBot for {config.TRADING_PAIR}")
        logger.info(f"Configuration - Leverage: {config.LEVERAGE}x, Position Size: {config.POSITION_SIZE}, Max Positions: {config.MAX_POSITIONS}")
        
        while True:
            try:
                # Check if we can open new positions
                if len(self.active_positions) >= config.MAX_POSITIONS:
                    logger.info("Maximum positions reached, waiting...")
                    time.sleep(60)
                    continue
                
                # Get historical data and calculate indicators
                df = self.get_historical_data()
                df = self.calculate_indicators(df)
                
                # Check entry conditions
                conditions = self.check_entry_conditions(df)
                
                current_time = time.time()
                if current_time - self.last_trade_time < self.min_trade_interval:
                    logger.debug("Waiting for minimum trade interval...")
                    time.sleep(1)
                    continue
                
                # Execute trades based on conditions
                if conditions['long']:
                    logger.info("Long entry conditions met, placing order...")
                    order = self.place_order(SIDE_BUY, config.POSITION_SIZE)
                    if order:
                        logger.info(f"Long position opened at {order['avgPrice']}")
                        self.last_trade_time = current_time
                
                elif conditions['short']:
                    logger.info("Short entry conditions met, placing order...")
                    order = self.place_order(SIDE_SELL, config.POSITION_SIZE)
                    if order:
                        logger.info(f"Short position opened at {order['avgPrice']}")
                        self.last_trade_time = current_time
                
                time.sleep(1)  # Wait 1 second before next iteration
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                logger.info("Waiting 60 seconds before retrying...")
                time.sleep(60)  # Wait 1 minute before retrying

    

if __name__ == "__main__":
    bot = BiBot()
    bot.run() 