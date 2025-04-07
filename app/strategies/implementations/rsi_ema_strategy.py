from typing import List
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

from app.config.settings import BiBotConfig
from app.strategies.strategy_base import TradingStrategy
from app.utils.binance.client import KlineData
from app.utils.data_converter import convert_klines_to_dataframe
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)


class RsiEmaStrategy(TradingStrategy):
    """
    RSI + EMA Crossover Strategy
    """

    def __init__(self, config: BiBotConfig):
        """
        Initialize the strategy with configuration parameters

        Args:
            config: Strategy configuration object
        """
        self.config = config
        self.rsi_period = config.rsi_ema.rsi_period
        self.rsi_overbought = config.rsi_ema.rsi_overbought
        self.rsi_oversold = config.rsi_ema.rsi_oversold
        self.ema_fast = config.rsi_ema.ema_fast
        self.ema_slow = config.rsi_ema.ema_slow

        logger.info(f"Initialized RSI+EMA Strategy with parameters:")
        logger.info(f"RSI Period: {self.rsi_period}")
        logger.info(f"RSI Overbought: {self.rsi_overbought}")
        logger.info(f"RSI Oversold: {self.rsi_oversold}")
        logger.info(f"EMA Fast: {self.ema_fast}")
        logger.info(f"EMA Slow: {self.ema_slow}")

    def generate_trading_signals(self, klines: List[KlineData]) -> dict:
        """
        Generate trading signals based on RSI and EMA indicators

        Args:
            klines: List of KlineData objects containing historical price data

        Returns:
            Dictionary containing:
                - 'data': DataFrame with indicators
                - 'signals': Dictionary with 'long' and 'short' boolean keys
        """
        # Convert klines to DataFrame for technical analysis
        df = convert_klines_to_dataframe(klines)

        # Calculate RSI
        rsi_indicator = RSIIndicator(close=df["close"], window=self.rsi_period)
        df["rsi"] = rsi_indicator.rsi()

        # Calculate EMAs
        ema_fast = EMAIndicator(close=df["close"], window=self.ema_fast)
        ema_slow = EMAIndicator(close=df["close"], window=self.ema_slow)
        df["ema_fast"] = ema_fast.ema_indicator()
        df["ema_slow"] = ema_slow.ema_indicator()

        # Generate signals
        df["long_signal"] = (df["rsi"] < self.rsi_oversold) & (  # RSI oversold
            df["ema_fast"] > df["ema_slow"]
        )  # Fast EMA above slow EMA

        df["short_signal"] = (df["rsi"] > self.rsi_overbought) & (  # RSI overbought
            df["ema_fast"] < df["ema_slow"]
        )  # Fast EMA below slow EMA

        # Get the latest signal
        latest_signal = {
            "long": bool(df["long_signal"].iloc[-1]),
            "short": bool(df["short_signal"].iloc[-1]),
        }

        logger.debug(f"Latest RSI: {df['rsi'].iloc[-1]:.2f}")
        logger.debug(f"Latest EMA Fast: {df['ema_fast'].iloc[-1]:.2f}")
        logger.debug(f"Latest EMA Slow: {df['ema_slow'].iloc[-1]:.2f}")
        logger.debug(f"Trading signals: {latest_signal}")

        return {"data": df, "signals": latest_signal}
