from pydantic import BaseModel, field_validator
from typing import Union, Any


class BinanceOrder(BaseModel):
    """Model for Binance order responses"""
    orderId: str
    symbol: str
    status: str
    clientOrderId: str
    price: str
    avgPrice: str
    origQty: str
    executedQty: str
    type: str
    side: str
    
    @field_validator('orderId', mode='before')
    @classmethod
    def convert_order_id_to_str(cls, v: Any) -> str:
        """Convert integer order ID to string"""
        return str(v)
    
    class Config:
        """Pydantic config"""
        extra = "allow"  # Allow additional fields from Binance API