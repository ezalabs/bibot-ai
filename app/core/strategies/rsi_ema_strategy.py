import ta
from app.utils.logger import get_logger
import app.config as config
from .strategy_base import TradingStrategy

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
        logger.info(f"Initializing {self.get_name()} with RSI({config.RSI_PERIOD}) "
                    f"and EMA({config.EMA_FAST}/{config.EMA_SLOW})")
    
    def generate_trading_signals(self, df):
        """
        Generate trading signals based on RSI and EMA indicators.
        
        Args:
            df (pandas.DataFrame): Raw historical price data
            
        Returns:
            dict: Dictionary with 'data' (DataFrame with indicators) and
                  'signals' (dict with 'long' and 'short' entry signals)
        """
        logger.debug("Generating trading signals using RSI-EMA strategy")
        
        try:
            # Calculate RSI
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=config.RSI_PERIOD).rsi()
            logger.debug(f"Current RSI: {df['rsi'].iloc[-1]:.2f}")
            
            # Calculate EMAs
            df['ema_fast'] = ta.trend.EMAIndicator(df['close'], window=config.EMA_FAST).ema_indicator()
            df['ema_slow'] = ta.trend.EMAIndicator(df['close'], window=config.EMA_SLOW).ema_indicator()
            
            logger.debug(f"Current EMAs - Fast: {df['ema_fast'].iloc[-1]:.2f}, "f"Slow: {df['ema_slow'].iloc[-1]:.2f}")
            
            # Check entry conditions
            last_row = df.iloc[-1]
            
            # RSI conditions
            rsi_oversold = last_row['rsi'] < config.RSI_OVERSOLD
            rsi_overbought = last_row['rsi'] > config.RSI_OVERBOUGHT
            
            # EMA crossover
            ema_cross_up = (df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and
                           df['ema_fast'].iloc[-2] <= df['ema_slow'].iloc[-2])
            
            ema_cross_down = (df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1] and
                             df['ema_fast'].iloc[-2] >= df['ema_slow'].iloc[-2])
            
            # Generate signals
            signals = {
                'long': rsi_oversold and ema_cross_up,
                'short': rsi_overbought and ema_cross_down
            }
            
            logger.debug(f"Entry signals - Long: {signals['long']}, Short: {signals['short']}")
            
            return {
                'data': df,
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"Error generating trading signals: {e}")
            raise
