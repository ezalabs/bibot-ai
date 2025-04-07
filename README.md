# BiBot - Python Trading Bot for Binance Futures

A Python-based trading bot for Binance Futures that implements various trading strategies.

## Features
- Automated trading using RSI and EMA crossover strategy [Default]
- Take profit and stop loss order management
- Position tracking with state persistence across restarts
- Configurable trading parameters
- Support for testnet trading
- Support for custom strategies

## Disclaimer

This bot is for educational purposes only. Always test thoroughly on testnet before using real funds. Trading cryptocurrencies involves significant risk. 

## Local Setup with Poetry

### Prerequisites
- Ensure you have Python 3.9 or higher installed on your machine.
- Install Poetry for dependency management. You can follow the instructions on [Poetry's official website](https://python-poetry.org/docs/#installation).

### Clone the Repository
First, clone the repository to your local machine:

```bash
git clone https://github.com/ezalabs/bibot.git
cd bibot
```

### Install Dependencies
Use Poetry to install the project dependencies:

```bash
poetry install
```

### Running the Bot
To run the bot locally, you can use the following command:

```bash
poetry run python main.py
```

To clean up all tracked positions and exit:

```bash
poetry run python main.py --cleanup
```

## Docker Setup

### Prerequisites
- Ensure you have Docker installed on your machine. You can download it from [Docker's official website](https://www.docker.com/get-started).

### Building the Docker Image
To build the Docker image for BiBot, navigate to the project directory and run the following command:

```bash
docker build -t bibot .
```

### Running the Docker Container
To run the Docker container, use the following command, ensuring to pass your environment variables from the `.env` file:

```bash
docker run -v $(pwd)/cache:/app/cache --env-file .env bibot
```

Note: The volume mount `-v $(pwd)/cache:/app/cache` is used to persist the cache between container restarts.

## Cache System

BiBot now includes a state persistence system that saves active positions to a local cache file. This ensures that:

1. If the bot is restarted, it will reload any open positions and continue managing them
2. No positions are orphaned if the bot crashes or is shut down
3. All stop-loss and take-profit orders are properly tracked and managed

The cache files are stored in a `cache` directory in the project root, with filenames based on the trading pair being used.

## Environment Variables
The following environment variables are required for the bot to function correctly. You can set these in your `.env` file:

```plaintext
# Binance API credentials
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Logging configuration
LOG_LEVEL=DEBUG  # Default: DEBUG (Options: DEBUG, INFO, WARNING, ERROR, CRITICAL)

# Trading configuration
TRADING_PAIR=BTCUSDT  # Default: BTCUSDT
POSITION_SIZE=0.01     # Default: 0.01 (in BTC)
LEVERAGE=5             # Default: 5

# Scalping parameters
TAKE_PROFIT_PERCENTAGE=0.1  # Default: 0.1%
STOP_LOSS_PERCENTAGE=0.05    # Default: 0.05%
MAX_POSITIONS=3               # Default: 3

# Technical analysis parameters
RSI_PERIOD=14                 # Default: 14
RSI_OVERBOUGHT=70             # Default: 60
RSI_OVERSOLD=30               # Default: 40
EMA_FAST=9                    # Default: 9
EMA_SLOW=21                   # Default: 21

# Strategy
STRATEGY="CUSTOM_STRATEGY" # Default: RSI_EMA

# Testnet configuration
USE_TESTNET=True              # Default: True (Set to False for live trading)
```

### Example `.env` File
Here's an example of what your `.env` file might look like:

```plaintext
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
LOG_LEVEL=INFO
TRADING_PAIR=BTCUSDT
POSITION_SIZE=0.01
LEVERAGE=5
TAKE_PROFIT_PERCENTAGE=0.1
STOP_LOSS_PERCENTAGE=0.05
MAX_POSITIONS=3
RSI_PERIOD=14
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30
EMA_FAST=9
EMA_SLOW=21
USE_TESTNET=True
```

## Usage
Once the bot is running, it will:

1. Connect to Binance Futures (testnet or mainnet based on configuration)
2. Load any existing positions from the cache
3. Start monitoring the market for trade opportunities
4. Place trades with stop-loss and take-profit orders when conditions are met
5. Continuously monitor positions and clean up closed positions
6. Save state to cache when positions change or when the bot shuts down

## Implementing Custom Trading Strategies

BiBot is designed with an extensible architecture that allows you to easily implement custom trading strategies. The bot uses a strategy factory pattern along with type-safe Pydantic models for configuration.

### Strategy Architecture

The strategy system consists of three main components:

1. The `TradingStrategy` abstract base class defining the interface
2. A `StrategyFactory` responsible for creating and registering strategies
3. Individual strategy implementations (e.g., `RsiEmaStrategy`)

The core interface is defined in `app/strategies/strategy_base.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from app.models.strategy import TradingResult
from app.utils.binance.client import KlineData

class TradingStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    @abstractmethod
    def generate_trading_signals(self, klines: List[KlineData]) -> TradingResult:
        """
        Process historical data and generate trading signals.
        
        Args:
            klines: List of KlineData objects containing historical price/volume data
            
        Returns:
            A dictionary containing:
                - 'data': The processed data with indicators
                - 'signals': A dictionary with 'long' and 'short' boolean keys
        """
        pass
    
    def get_name(self) -> str:
        """Get the name of the strategy"""
        return self.__class__.__name__
```

### Data Conversion Utility

BiBot provides a utility function for converting Binance `KlineData` to pandas DataFrames, which makes it easier to perform technical analysis. This utility is available at `app/utils/data_converter.py`:

```python
from typing import List
import pandas as pd

from app.utils.binance.client import KlineData

def convert_klines_to_dataframe(klines: List[KlineData]) -> pd.DataFrame:
    """
    Convert a list of KlineData objects to a pandas DataFrame for technical analysis.
    
    Args:
        klines: List of KlineData objects containing historical price/volume data
        
    Returns:
        DataFrame with properly formatted columns and datetime index
    """
    # Create DataFrame from KlineData list
    df = pd.DataFrame([{
        'timestamp': k['timestamp'],
        'open': k['open'],
        'high': k['high'],
        'low': k['low'],
        'close': k['close'],
        'volume': k['volume'],
        'quote_volume': k['quote_volume'],
        'trades': k['trades'],
        'taker_buy_base': k['taker_buy_base'],
        'taker_buy_quote': k['taker_buy_quote']
    } for k in klines])
    
    # Convert timestamp to datetime and set as index
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    return df
```

### Creating a Custom Strategy

To implement your own strategy:

1. Create a new Python file in the `app/strategies/implementations` directory
2. Define a class that inherits from `TradingStrategy`
3. Implement the `generate_trading_signals` method
4. Register your strategy with the factory

Here's an example of a simple Moving Average Crossover strategy:

```python
from typing import List
import pandas as pd
from ta.trend import SMAIndicator

from app.strategies.strategy_base import TradingStrategy
from app.utils.binance.client import KlineData
from app.utils.data_converter import convert_klines_to_dataframe
from app.utils.logging.logger import get_logger

logger = get_logger()

class MaCrossStrategy(TradingStrategy):
    """Moving Average Crossover Strategy"""
    
    def __init__(self, config):
        """
        Initialize the MA Crossover strategy
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.short_window = 10
        self.long_window = 50
        logger.info(f"Initializing {self.get_name()} with MA({self.short_window}/{self.long_window})")
    
    def generate_trading_signals(self, klines: List[KlineData]) -> dict:
        """
        Generate trading signals based on Moving Average crossovers
        
        Args:
            klines: List of KlineData objects containing historical price data
            
        Returns:
            Dictionary containing:
                - 'data': DataFrame with indicators
                - 'signals': Dictionary with 'long' and 'short' boolean keys
        """
        # Convert klines to DataFrame for technical analysis
        df = convert_klines_to_dataframe(klines)
        
        # Calculate moving averages
        df['short_ma'] = SMAIndicator(df['close'], window=self.short_window).sma_indicator()
        df['long_ma'] = SMAIndicator(df['close'], window=self.long_window).sma_indicator()
        
        # Generate signals
        df['long_signal'] = (df['short_ma'] > df['long_ma']) & (df['short_ma'].shift(1) <= df['long_ma'].shift(1))
        df['short_signal'] = (df['short_ma'] < df['long_ma']) & (df['short_ma'].shift(1) >= df['long_ma'].shift(1))
        
        # Get the latest signal
        latest_signal = {
            'long': bool(df['long_signal'].iloc[-1]),
            'short': bool(df['short_signal'].iloc[-1])
        }
        
        logger.debug(f"Latest MA Fast: {df['short_ma'].iloc[-1]:.2f}")
        logger.debug(f"Latest MA Slow: {df['long_ma'].iloc[-1]:.2f}")
        logger.debug(f"Trading signals: {latest_signal}")
        
        return {
            'data': df,
            'signals': latest_signal
        }
```

Then you can set the strategy in your `.env` file:

```plaintext
STRATEGY=MA_CROSS
```

### Registering Your Strategy

To make your strategy available to the factory, add it to the `app/strategies/__init__.py` file:

```python
from app.strategies.strategy_base import TradingStrategy, TradingResult, TradingSignals
from app.strategies.implementations.rsi_ema_strategy import RsiEmaStrategy
from app.strategies.implementations.ma_cross_strategy import MaCrossStrategy
from app.strategies.factory import StrategyFactory

# Register all available strategies
StrategyFactory.register_strategy("RSI_EMA", RsiEmaStrategy)
StrategyFactory.register_strategy("MA_CROSS", MaCrossStrategy)

# Export classes for easier imports
__all__ = [
    "TradingStrategy", 
    "TradingResult", 
    "TradingSignals",
    "RsiEmaStrategy", 
    "MaCrossStrategy", 
    "StrategyFactory"
]
```

### Using Your Custom Strategy

To use your custom strategy with BiBot, you can either specify it in your environment configuration or pass it directly to the BiBot constructor:

```python
# In .env file
STRATEGY=MA_CROSS

# Or when creating the BiBot instance directly
from app.core.bibot import BiBot
from app.config.settings import load_config

config = load_config()
config.strategy = "MA_CROSS"  # Override strategy
bot = BiBot(config=config)
```

The BiBot class automatically uses the StrategyFactory to create the right strategy:

```python
# Simplified from app/core/bibot.py
self.strategy = StrategyFactory.create_strategy(config=self.config)
logger.info(f"Using trading strategy: {self.strategy.get_name()}")
```

### Strategy Selection

The StrategyFactory handles strategy creation and selection based on your configuration:

```python
# app/strategies/factory.py
from typing import Dict, Type, Optional
from app.strategies.strategy_base import TradingStrategy
from app.config.settings import BiBotConfig, load_config

class StrategyFactory:
    """Factory for creating trading strategy instances"""
    
    # Registry of available strategies
    _strategies: Dict[str, Type[TradingStrategy]] = {}
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[TradingStrategy]) -> None:
        """
        Register a strategy with the factory
        
        Args:
            name: Name identifier for the strategy
            strategy_class: Strategy class to register
        """
        cls._strategies[name] = strategy_class
    
    @classmethod
    def create_strategy(cls, name: Optional[str] = None, config: Optional[BiBotConfig] = None) -> TradingStrategy:
        """
        Create a strategy instance
        
        Args:
            name: Optional name of strategy to create (defaults to config.strategy)
            config: Optional configuration to pass to strategy
            
        Returns:
            Instantiated strategy
        """
        config = config or load_config()
        name = name or config.strategy
        
        strategy_class = cls._strategies.get(name)
        if not strategy_class:
            # Fallback to default if strategy not found
            fallback = next(iter(cls._strategies.values()))
            return fallback(config=config)
        
        return strategy_class(config=config)
```

Then you can set the strategy in your `.env` file:

```plaintext
STRATEGY=MA_CROSS
```

### Best Practices for Custom Strategies

1. **Type Safety**: Use type hints and Pydantic models for better code quality
2. **Configuration**: Load parameters from the centralized Pydantic-based config
3. **Logging**: Use the logger to provide informative debug messages about your strategy's decisions
4. **Error Handling**: Implement proper error handling within your strategy
5. **Testing**: Write unit tests for your strategy logic
6. **Documentation**: Add docstrings to your strategy class and methods
7. **Data Conversion**: Use the provided `convert_klines_to_dataframe` utility for consistent handling of market data

By following this pattern, you can create and experiment with various trading strategies while keeping the core trading infrastructure intact and type-safe.

## Contributing
Feel free to contribute to the project by submitting issues or pull requests.

## License
This project is licensed under the MIT License.
