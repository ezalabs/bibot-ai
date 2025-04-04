import pandas as pd
import ta
from app.config.settings import load_config, BiBotConfig
from app.models.strategy import TradingResult, TradingSignals
from app.strategies.strategy_base import TradingStrategy
from app.utils.logging.logger import get_logger

# Configure logging
logger = get_logger()

class RsiEmaStrategy(TradingStrategy):
    """
    Trading strategy based on RSI overbought/oversold conditions
    combined with EMA crossovers.
    """
    
    def __init__(self):
        """
        Initialize the RSI-EMA strategy.
        """
        super().__init__()
        # Load config
        self.config: BiBotConfig = load_config()
        logger.info(f"Initializing {self.get_name()} with RSI({self.config.rsi_ema.rsi_period}) "
                    f"and EMA({self.config.rsi_ema.ema_fast}/{self.config.rsi_ema.ema_slow})")
    
    def generate_trading_signals(self, df: pd.DataFrame) -> TradingResult:
        """
        Generate trading signals based on RSI and EMA indicators.
        
        Args:
            df: Raw historical price data
            
        Returns:
            Dictionary with 'data' (DataFrame with indicators) and
            'signals' (dict with 'long' and 'short' entry signals)
        """
        logger.debug("Generating trading signals using RSI-EMA strategy")
        
        try:
            # Calculate RSI
            df['rsi'] = ta.momentum.RSIIndicator(
                df['close'], 
                window=self.config.rsi_ema.rsi_period
            ).rsi()
            logger.debug(f"Current RSI: {df['rsi'].iloc[-1]:.2f}")
            
            # Calculate EMAs
            df['ema_fast'] = ta.trend.EMAIndicator(
                df['close'], 
                window=self.config.rsi_ema.ema_fast
            ).ema_indicator()
            
            df['ema_slow'] = ta.trend.EMAIndicator(
                df['close'], 
                window=self.config.rsi_ema.ema_slow
            ).ema_indicator()
            
            logger.debug(f"Current EMAs - Fast: {df['ema_fast'].iloc[-1]:.2f}, "
                         f"Slow: {df['ema_slow'].iloc[-1]:.2f}")
            
            # Check entry conditions
            last_row = df.iloc[-1]
            
            # RSI conditions
            rsi_oversold = last_row['rsi'] < self.config.rsi_ema.rsi_oversold
            rsi_overbought = last_row['rsi'] > self.config.rsi_ema.rsi_overbought
            
            # EMA crossover
            ema_cross_up = (df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and
                           df['ema_fast'].iloc[-2] <= df['ema_slow'].iloc[-2])
            
            ema_cross_down = (df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1] and
                             df['ema_fast'].iloc[-2] >= df['ema_slow'].iloc[-2])
            
            logger.debug(f"RSI: {last_row['rsi']:.2f} (Oversold: {rsi_oversold}, "
                         f"Overbought: {rsi_overbought})")
            logger.debug(f"EMA Crossover - Up: {ema_cross_up}, Down: {ema_cross_down}")
            
            # Generate signals
            signals = TradingSignals(
                long=rsi_oversold and ema_cross_up,
                short=rsi_overbought and ema_cross_down
            )
            
            logger.debug(f"Entry signals - Long: {signals['long']}, Short: {signals['short']}")
            
            return TradingResult(
                data=df,
                signals=signals
            )
            
        except Exception as e:
            logger.error(f"Error generating trading signals: {e}")
            raise
