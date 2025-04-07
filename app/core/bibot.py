import time
from typing import Optional

from app.config.settings import BiBotConfig, load_config
from app.utils.logging.logger import get_logger
from app.strategies.factory import StrategyFactory
from app.services.order_manager import OrderManager
from app.utils.binance.client import BinanceClient
from app.core.market_data import MarketData
from app.services.position_manager import PositionManager

# Configure logging
logger = get_logger(__name__)

class BiBot:
    """
    BiBot - A Python-based trading bot for Binance Futures
    that implements scalping strategies.
    """
    
    def __init__(self, config: Optional[BiBotConfig] = None):
        """
        Initialize the trading bot with the given configuration
        
        Args:
            config: Configuration object, loaded from environment if not provided
        """
        self.config = config or load_config()
        logger.info("Initializing BiBot ...")
        
        # Initialize client
        self.client = BinanceClient(self.config)
        
        # Initialize services
        self.market_data = MarketData(self.client, self.config)
        self.position_manager = PositionManager(self.client, self.config)
        self.order_manager = OrderManager(self.client, self.config)
        
        # Initialize strategy
        self.strategy = StrategyFactory.create_strategy(config=self.config)
        logger.info(f"Using trading strategy: {self.strategy.get_name()}")
        
        # Load positions
        self.position_manager.load_positions()
        
        logger.info("BiBot initialization completed")
        

    def run(self) -> None:
        """Main bot loop"""
        logger.info(f"Starting BiBot for {self.config.trading.trading_pair}")
        logger.info(f"Configuration - Leverage: {self.config.trading.leverage}x, Position Size: {self.config.trading.position_size}, Max Positions: {self.config.trading.max_positions}")
        
        while True:
            try:
                # Check positions periodically
                self.position_manager.check_closed_positions()
                
                # Skip if we're at position limit
                if self.position_manager.has_reached_position_limit():
                    logger.info("Maximum positions reached, waiting...")
                    time.sleep(10)
                    continue
                
                # Get market data
                df = self.market_data.get_historical_data()
                
                # Generate trading signals
                result = self.strategy.generate_trading_signals(df)
                signals = result['signals']
                
                # Execute trades based on signals
                if signals['long']:
                    logger.info("Long entry conditions met, placing order...")
                    position = self.order_manager.open_long_position(
                        self.config.trading.position_size
                    )
                    if position:
                        self.position_manager.track_position(position)
                        logger.info(f"Long position opened at {position.entry_price}")
                
                elif signals['short']:
                    logger.info("Short entry conditions met, placing order...")
                    position = self.order_manager.open_short_position(
                        self.config.trading.position_size
                    )
                    if position:
                        self.position_manager.track_position(position)
                        logger.info(f"Short position opened at {position.entry_price}")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                logger.info("Waiting 60 seconds before retrying...")
                time.sleep(60)
