from typing import Optional
from app.config.settings import BiBotConfig, load_config
from app.utils.binance.client import BinanceClient
from app.core.market_data import MarketData
from app.services.position_manager import PositionManager
from app.services.order_manager import OrderManager
from app.strategies.factory import StrategyFactory

class ServiceRegistry:
    """
    Central registry for application services.
    Manages initialization and access to shared services.
    """
    
    def __init__(self, config: Optional[BiBotConfig] = None):
        """
        Initialize the service registry with configuration
        
        Args:
            config: Configuration object, loaded from environment if not provided
        """
        self.config = config or load_config()
        
        # Initialize the client first
        self._client = None
        
        # Service instances (lazy loaded)
        self._market_data = None
        self._position_manager = None
        self._order_manager = None
        self._strategy = None
    
    @property
    def client(self):
        """Lazy-loaded Binance client"""
        if self._client is None:
            self._client = BinanceClient(self.config)
        return self._client
    
    @property
    def market_data(self):
        """Lazy-loaded market data service"""
        if self._market_data is None:
            self._market_data = MarketData(self.client, self.config)
        return self._market_data
    
    @property
    def position_manager(self):
        """Lazy-loaded position manager service"""
        if self._position_manager is None:
            self._position_manager = PositionManager(self.client, self.config)
            self._position_manager.load_positions()
        return self._position_manager
    
    @property
    def order_manager(self):
        """Lazy-loaded order manager service"""
        if self._order_manager is None:
            self._order_manager = OrderManager(self.client, self.config)
        return self._order_manager
    
    @property
    def strategy(self):
        """Lazy-loaded trading strategy"""
        if self._strategy is None:
            self._strategy = StrategyFactory.create_strategy(config=self.config)
        return self._strategy
