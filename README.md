# BiBot - Python-based Trading Bot for Binance Futures

## Overview
BiBot is a Python-based trading bot designed for Binance Futures that implements scalping strategies with state persistence across restarts.

## Features
- Automated trading using RSI and EMA crossover strategy
- Take profit and stop loss order management
- Position tracking with state persistence across restarts
- Configurable trading parameters
- Support for testnet trading

## Disclaimer

This bot is for educational purposes only. Always test thoroughly on testnet before using real funds. Trading cryptocurrencies involves significant risk. 

## Local Setup with Poetry

### Prerequisites
- Ensure you have Python 3.9 or higher installed on your machine.
- Install Poetry for dependency management. You can follow the instructions on [Poetry's official website](https://python-poetry.org/docs/#installation).

### Clone the Repository
First, clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/bibot.git
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
docker build -t binbot .
```

### Running the Docker Container
To run the Docker container, use the following command, ensuring to pass your environment variables from the `.env` file:

```bash
docker run -v $(pwd)/cache:/app/cache --env-file .env binbot
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

## Contributing
Feel free to contribute to the project by submitting issues or pull requests.

## License
This project is licensed under the MIT License.