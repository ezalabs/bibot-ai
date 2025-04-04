from pydantic import BaseModel, Field, field_validator, model_validator
import os
from typing import Optional, Literal, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BinanceCredentials(BaseModel):
    """Binance API credentials configuration"""
    api_key: str
    api_secret: str
    
    @field_validator('api_key', 'api_secret')
    @classmethod
    def validate_credentials(cls, v):
        if not v:
            raise ValueError("API credentials cannot be empty")
        return v

class TradingConfig(BaseModel):
    """Trading parameters configuration"""
    trading_pair: str = Field(default="BTCUSDT", description="Trading pair symbol")
    position_size: float = Field(default=0.01, gt=0, description="Position size in base asset")
    leverage: int = Field(default=5, gt=0, le=125, description="Leverage for futures trading")
    take_profit_percentage: float = Field(default=0.1, gt=0, description="Take profit percentage")
    stop_loss_percentage: float = Field(default=0.05, gt=0, description="Stop loss percentage")
    max_positions: int = Field(default=3, ge=1, description="Maximum number of concurrent positions")
    use_testnet: bool = Field(default=True, description="Whether to use Binance testnet")

class RsiEmaConfig(BaseModel):
    """RSI and EMA strategy specific configuration"""
    rsi_period: int = Field(default=14, gt=0, description="RSI indicator period")
    rsi_overbought: float = Field(default=70.0, ge=50.0, le=100.0, description="RSI overbought threshold")
    rsi_oversold: float = Field(default=30.0, ge=0.0, le=50.0, description="RSI oversold threshold")
    ema_fast: int = Field(default=9, gt=0, description="Fast EMA period")
    ema_slow: int = Field(default=21, gt=0, description="Slow EMA period")
    
    @field_validator('ema_slow')
    @classmethod
    def validate_ema_relationship(cls, v, info):
        if 'ema_fast' in info.data and v <= info.data['ema_fast']:
            raise ValueError(f"Slow EMA period ({v}) must be greater than fast EMA period ({info.data['ema_fast']})")
        return v

class LoggingConfig(BaseModel):
    """Logging configuration"""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", 
        description="Logging level"
    )

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
                'rsi_overbought': float(values.get('rsi_overbought', os.getenv('RSI_OVERBOUGHT', 70))),
                'rsi_oversold': float(values.get('rsi_oversold', os.getenv('RSI_OVERSOLD', 30))),
                'ema_fast': int(values.get('ema_fast', os.getenv('EMA_FAST', 9))),
                'ema_slow': int(values.get('ema_slow', os.getenv('EMA_SLOW', 21))),
            },
            'logging': {
                'log_level': values.get('log_level', os.getenv('LOG_LEVEL', 'INFO')).upper(),
            },
            'strategy': values.get('strategy', os.getenv('STRATEGY', 'RSI_EMA')),
        }
        return structured

def load_config() -> BiBotConfig:
    """
    Load configuration from environment variables and validate using Pydantic.
    
    Returns:
        BiBotConfig: Validated configuration object
    
    Raises:
        ValidationError: If the configuration is invalid
    """
    try:
        config = BiBotConfig()
        print(f"Configuration loaded successfully with trading pair: {config.trading.trading_pair}")
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        raise