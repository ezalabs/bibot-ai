from typing import Any, Optional
from pydantic import BaseModel


class BinancePosition(BaseModel):
    """Model for Binance position information"""
    symbol: str
    positionAmt: str
    entryPrice: str
    markPrice: str
    unRealizedProfit: str
    liquidationPrice: str
    leverage: Optional[str] = "1"  # Making this optional with a default
    marginType: Optional[str] = ""  # Making this optional with a default
    isolatedMargin: str
    positionSide: str
    
    class Config:
        """Pydantic config"""
        extra = "allow"
