from typing import Any
from pydantic import BaseModel


class BinancePosition(BaseModel):
    """Model for Binance position information"""
    symbol: str
    positionAmt: str
    entryPrice: str
    markPrice: str
    unRealizedProfit: str
    liquidationPrice: str
    leverage: str
    marginType: str
    isolatedMargin: str
    positionSide: str
    
    class Config:
        """Pydantic config"""
        extra = "allow"
