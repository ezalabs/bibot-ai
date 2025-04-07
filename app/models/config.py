from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal

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
    rsi_overbought: float = Field(default=60.0, ge=50.0, le=100.0, description="RSI overbought threshold")
    rsi_oversold: float = Field(default=40.0, ge=0.0, le=50.0, description="RSI oversold threshold")
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