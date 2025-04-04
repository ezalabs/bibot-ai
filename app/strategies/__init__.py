from app.strategies.strategy_base import TradingStrategy
from app.strategies.implementations.rsi_ema_strategy import RsiEmaStrategy
from app.strategies.factory import StrategyFactory

# Register all strategies with the factory
StrategyFactory.register_strategy("RSI_EMA", RsiEmaStrategy)

__all__ = [
    'TradingStrategy',
    'RsiEmaStrategy',
    'StrategyFactory'
]