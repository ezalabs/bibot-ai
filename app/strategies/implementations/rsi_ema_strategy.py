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
    RSI + EMA Strategy with improved signal generation
    """

    def __init__(self, config: BiBotConfig):
        """
        Initialize the strategy with configuration parameters

        Args:
            config: Strategy configuration object
        """
        self.config = config
        
        # Use configuration parameters or defaults
        self.rsi_period = getattr(config.rsi_ema, 'rsi_period', 14)
        self.rsi_overbought = getattr(config.rsi_ema, 'rsi_overbought', 60)
        self.rsi_oversold = getattr(config.rsi_ema, 'rsi_oversold', 40)
        self.ema_fast = getattr(config.rsi_ema, 'ema_fast', 9)
        self.ema_slow = getattr(config.rsi_ema, 'ema_slow', 21)

        logger.info(f"Initialized RSI+EMA Strategy with parameters:")
        logger.info(f"RSI Period: {self.rsi_period}")
        logger.info(f"RSI Overbought: {self.rsi_overbought}")
        logger.info(f"RSI Oversold: {self.rsi_oversold}")
        logger.info(f"EMA Fast: {self.ema_fast}")
        logger.info(f"EMA Slow: {self.ema_slow}")

    def generate_trading_signals(self, klines: List[KlineData]) -> dict:
        """
        Generate trading signals based on RSI and EMA indicators with improved logic

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

        # Calculate RSI change (to detect reversals)
        df["rsi_change"] = df["rsi"] - df["rsi"].shift(1)
        
        # Calculate EMA slopes (to detect trend direction)
        df["ema_fast_slope"] = df["ema_fast"] - df["ema_fast"].shift(1)
        df["ema_slow_slope"] = df["ema_slow"] - df["ema_slow"].shift(1)

        # Generate long signals (more lenient conditions)
        # 1. RSI is below oversold and starting to turn up
        rsi_oversold_turning_up = (df["rsi"] < self.rsi_oversold) & (df["rsi_change"] > 0)
        
        # 2. OR RSI was recently oversold (within last 3 bars) and is rising
        rsi_recently_oversold = (df["rsi"].shift(1) < self.rsi_oversold) | (df["rsi"].shift(2) < self.rsi_oversold)
        rsi_rising = df["rsi_change"] > 0
        recently_oversold_and_rising = rsi_recently_oversold & rsi_rising
        
        # 3. Fast EMA is above slow EMA OR Fast EMA is rising faster than slow EMA
        ema_aligned_for_uptrend = (df["ema_fast"] >= df["ema_slow"]) | (df["ema_fast_slope"] > df["ema_slow_slope"])
        
        # Combined long signal conditions
        df["long_signal"] = (
            (rsi_oversold_turning_up | recently_oversold_and_rising) & 
            ema_aligned_for_uptrend
        )

        # Generate short signals (more lenient conditions)
        # 1. RSI is above overbought and starting to turn down
        rsi_overbought_turning_down = (df["rsi"] > self.rsi_overbought) & (df["rsi_change"] < 0)
        
        # 2. OR RSI was recently overbought (within last 3 bars) and is falling
        rsi_recently_overbought = (df["rsi"].shift(1) > self.rsi_overbought) | (df["rsi"].shift(2) > self.rsi_overbought)
        rsi_falling = df["rsi_change"] < 0
        recently_overbought_and_falling = rsi_recently_overbought & rsi_falling
        
        # 3. Fast EMA is below slow EMA OR Fast EMA is falling faster than slow EMA
        ema_aligned_for_downtrend = (df["ema_fast"] <= df["ema_slow"]) | (df["ema_fast_slope"] < df["ema_slow_slope"])
        
        # Combined short signal conditions
        df["short_signal"] = (
            (rsi_overbought_turning_down | recently_overbought_and_falling) & 
            ema_aligned_for_downtrend
        )

        # Get the latest signal
        latest_signal = {
            "long": bool(df["long_signal"].iloc[-1]),
            "short": bool(df["short_signal"].iloc[-1]),
        }

        # Log detailed signal information
        logger.debug(f"Latest RSI: {df['rsi'].iloc[-1]:.2f} (change: {df['rsi_change'].iloc[-1]:.2f})")
        logger.debug(f"Latest EMA Fast: {df['ema_fast'].iloc[-1]:.2f} (slope: {df['ema_fast_slope'].iloc[-1]:.4f})")
        logger.debug(f"Latest EMA Slow: {df['ema_slow'].iloc[-1]:.2f} (slope: {df['ema_slow_slope'].iloc[-1]:.4f})")
        logger.debug(f"Long conditions - RSI turning up: {bool(rsi_oversold_turning_up.iloc[-1])}, Recently oversold: {bool(recently_oversold_and_rising.iloc[-1])}")
        logger.debug(f"Short conditions - RSI turning down: {bool(rsi_overbought_turning_down.iloc[-1])}, Recently overbought: {bool(recently_overbought_and_falling.iloc[-1])}")
        logger.debug(f"Trading signals: {latest_signal}")

        return {"data": df, "signals": latest_signal}
