from binance.client import Client
import time
import config
import logging
from binance.exceptions import BinanceAPIException
import requests.exceptions

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
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

    

if __name__ == "__main__":
    bot = BiBot()