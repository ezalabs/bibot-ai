# BiBot - Python-based Trading Bot for Binance Futures

## Overview
BiBot is a Python-based trading bot designed for Binance Futures that implements scalping strategies.

## Features

- Scalping strategy implementation
- Testnet support for safe testing
- Technical analysis indicators
- Risk management with stop-loss and take-profit
- Position sizing management

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

### Environment Variables
The following environment variables are required for the bot to function correctly. You can set these in your `.env` file:

```plaintext
# Binance API credentials
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

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
LOG_LEVEL=desired_log_level ex DEBUG, INFO, WARNING
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
docker run --name bibot --env-file .env bibot
```

## Usage
Once the bot is running, whether locally or in a Docker container, it will start trading based on the configured parameters and strategies.

## Disclaimer

This bot is for educational purposes only. Always test thoroughly on testnet before using real funds. Trading cryptocurrencies involves significant risk. 

## Contributing
Feel free to contribute to the project by submitting issues or pull requests.

## License
This project is licensed under the MIT License.