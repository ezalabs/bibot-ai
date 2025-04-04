# BiBot - Python-based Trading Bot for Binance Futures

## Overview
BiBot is a Python-based trading bot designed for Binance Futures that implements scalping strategies.

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
RSI_OVERBOUGHT=70             # Default: 70
RSI_OVERSOLD=30               # Default: 30
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

BiBot is designed with an extensible architecture that allows you to easily implement custom trading strategies. By creating new classes that inherit from the base `TradingStrategy` class, you can define your own trading logic while reusing the core bot infrastructure.

### Strategy Architecture

The core of BiBot's strategy system is the `TradingStrategy` abstract base class:

```python
from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    @abstractmethod
    def generate_trading_signals(self, df):
        """
        Process historical data and generate trading signals.
        
        Args:
            df (pandas.DataFrame): Raw historical price/volume data
            
        Returns:
            dict: A dictionary containing:
                 - 'data': The DataFrame with added indicators (optional)
                 - 'signals': A dictionary with at least 'long' and 'short' boolean keys
        """
        pass
```

### Creating a Custom Strategy

To implement your own strategy:

1. Create a new Python file in the `app/strategies` directory
2. Define a class that inherits from `TradingStrategy`
3. Implement the `generate_trading_signals` method
4. Return a dictionary with your trading signals

Here's an example of a simple Moving Average Crossover strategy:

```python
import ta
import app.utils.logging
from app.strategies.strategy_base import TradingStrategy

logger = get_logger()

class MaCrossStrategy(TradingStrategy):
    def __init__(self):
        super().__init__()
        self.short_window = 10
        self.long_window = 50
        logger.info(f"Initializing {self.get_name()} with MA({self.short_window}/{self.long_window})")
    
    def generate_trading_signals(self, df):
        """Generate trading signals based on Moving Average crossovers"""
        logger.debug("Generating signals using MA Cross strategy")
        
        # Calculate moving averages
        df['short_ma'] = ta.trend.SMAIndicator(df['close'], window=self.short_window).sma_indicator()
        df['long_ma'] = ta.trend.SMAIndicator(df['close'], window=self.long_window).sma_indicator()
        
        # Calculate crossover events
        ma_cross_up = (df['short_ma'].iloc[-1] > df['long_ma'].iloc[-1] and
                      df['short_ma'].iloc[-2] <= df['long_ma'].iloc[-2])
        
        ma_cross_down = (df['short_ma'].iloc[-1] < df['long_ma'].iloc[-1] and
                        df['short_ma'].iloc[-2] >= df['long_ma'].iloc[-2])
        
        # Generate signals
        signals = {
            'long': ma_cross_up,
            'short': ma_cross_down
        }
        
        return {
            'data': df,
            'signals': signals
        }
```

### Using Your Custom Strategy

To use your custom strategy with BiBot, you'll need to update the bot initialization in `app/bibot.py`:

```python
# Import your strategy
from app.strategies.my_custom_strategy import MyCustomStrategy

class BiBot:
    def __init__(self):
        # ... existing initialization code ...
        
        # Initialize with your custom strategy
        self.strategy = MyCustomStrategy()
        logger.info(f"Using trading strategy: {self.strategy.get_name()}")
        
        # ... rest of initialization ...
```

### Strategy Selection

For more advanced usage, you can implement strategy selection based on configuration:

```python
# In config.py
STRATEGY = os.getenv('STRATEGY') or 'RsiEma'  # Default strategy

# In bibot.py
from app.strategies.rsi_ema_strategy import RsiEmaStrategy
from app.strategies.ma_cross_strategy import MaCrossStrategy
# Import other strategies

STRATEGIES = {
    'RSI_EMA': RsiEmaStrategy,
    'MA_CROSS': MaCrossStrategy,
    # Add more strategies here
}

class BiBot:
    def __init__(self):
        # ... existing initialization code ...
        
        # Select strategy based on configuration
        strategy_class = STRATEGIES.get(config.STRATEGY)
        if not strategy_class:
            logger.warning(f"Strategy {config.STRATEGY} not found, using RsiEmaStrategy")
            strategy_class = RsiEmaStrategy
        
        self.strategy = strategy_class()
        logger.info(f"Using trading strategy: {self.strategy.get_name()}")
        
        # ... rest of initialization ...
```

Then you can set the strategy in your `.env` file:

```plaintext
STRATEGY=MA_CROSS
```

### Best Practices for Custom Strategies

1. **Logging**: Use the logger to provide informative debug messages about your strategy's decisions.
2. **Error Handling**: Implement proper error handling within your strategy.
3. **Configuration**: Consider using environment variables for strategy parameters.
4. **Documentation**: Document your strategy's logic, indicators, and signals.
5. **Testing**: Test your strategy with historical data before using it live.

By following this pattern, you can create and experiment with various trading strategies while keeping the core trading infrastructure intact.

## Contributing
Feel free to contribute to the project by submitting issues or pull requests.

## License
This project is licensed under the MIT License.
