from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime

class OrderInfo(BaseModel):
    """Information about an order associated with a position"""
    id: str 
    type: Literal['stop_loss', 'take_profit']

class Position(BaseModel):
    """Trading position model"""
    main_order_id: str
    entry_price: float
    side: Literal['BUY', 'SELL']
    quantity: float
    orders: List[OrderInfo]
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        """Pydantic configuration"""
        # Allow extra fields from dict initialization for backward compatibility
        extra = "allow"
