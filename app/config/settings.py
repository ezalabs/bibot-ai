from pydantic import BaseModel, Field, model_validator
import os
from typing import Optional
from dotenv import load_dotenv
import logging

from app.models.config import BinanceCredentials, LoggingConfig, RsiEmaConfig, TradingConfig

# Load environment variables
load_dotenv()

# Create a logger for this module
logger = logging.getLogger(__name__)

class BiBotConfig(BaseModel):
    """Main configuration for the trading bot"""
    credentials: BinanceCredentials
    trading: TradingConfig = Field(default_factory=TradingConfig)
    rsi_ema: RsiEmaConfig = Field(default_factory=RsiEmaConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    strategy: str = Field(default="RSI_EMA", description="Trading strategy to use")

    @model_validator(mode='before')
    @classmethod
    def build_from_flat_dict(cls, values):
        """
        Allows the config to be created from a flat dictionary or environment variables
        This makes it compatible with the existing config approach
        """
        if all(k in values for k in ['credentials', 'trading', 'rsi_ema', 'logging']):
            # Already in the right structure
            return values
            
        # Create a properly structured dict
        structured = {
            'credentials': {
                'api_key': values.get('api_key', os.getenv('BINANCE_API_KEY', '')),
                'api_secret': values.get('api_secret', os.getenv('BINANCE_API_SECRET', '')),
            },
            'trading': {
                'trading_pair': values.get('trading_pair', os.getenv('TRADING_PAIR', 'BTCUSDT')),
                'position_size': float(values.get('position_size', os.getenv('POSITION_SIZE', 0.01))),
                'leverage': int(values.get('leverage', os.getenv('LEVERAGE', 5))),
                'take_profit_percentage': float(values.get('take_profit_percentage', os.getenv('TAKE_PROFIT_PERCENTAGE', 0.1))),
                'stop_loss_percentage': float(values.get('stop_loss_percentage', os.getenv('STOP_LOSS_PERCENTAGE', 0.05))),
                'max_positions': int(values.get('max_positions', os.getenv('MAX_POSITIONS', 3))),
                'use_testnet': bool(values.get('use_testnet', os.getenv('USE_TESTNET', 'True').lower() == 'true')),
            },
            'rsi_ema': {
                'rsi_period': int(values.get('rsi_period', os.getenv('RSI_PERIOD', 14))),
                'rsi_overbought': float(values.get('rsi_overbought', os.getenv('RSI_OVERBOUGHT', 60))),
                'rsi_oversold': float(values.get('rsi_oversold', os.getenv('RSI_OVERSOLD', 40))),
                'ema_fast': int(values.get('ema_fast', os.getenv('EMA_FAST', 9))),
                'ema_slow': int(values.get('ema_slow', os.getenv('EMA_SLOW', 21))),
            },
            'logging': {
                'log_level': values.get('log_level', os.getenv('LOG_LEVEL', 'INFO')).upper(),
            },
            'strategy': values.get('strategy', os.getenv('STRATEGY', 'RSI_EMA')),
        }
        return structured

# Cache the config object
_config_cache: Optional[BiBotConfig] = None

def load_config() -> BiBotConfig:
    """
    Load configuration from environment variables and validate using Pydantic.
    Caches the configuration to avoid multiple loading.
    
    Returns:
        BiBotConfig: Validated configuration object
    
    Raises:
        ValidationError: If the configuration is invalid
    """
    global _config_cache
    
    # Return cached config if available
    if _config_cache is not None:
        return _config_cache
    
    try:
        config = BiBotConfig()
        logger.debug(f"Configuration loaded with trading pair: {config.trading.trading_pair}")
        
        # Cache the config
        _config_cache = config
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise