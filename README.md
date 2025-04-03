# BiBot

A Python-based trading bot for Binance Futures that implements scalping strategies.

## Setup

1. Install Poetry (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone the repository and install dependencies:
```bash
poetry install --no-root
```

3. Create a `.env` file with your Binance API credentials:
```
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

## Configuration

Edit `config.py` to adjust trading parameters:
- Trading pair
- Position size
- Stop loss and take profit levels
- Technical indicators parameters

## Usage

Run the bot using Poetry:
```bash
poetry run python main.py
```

## Features

- Scalping strategy implementation
- Testnet support for safe testing
- Technical analysis indicators
- Risk management with stop-loss and take-profit
- Position sizing management

## Disclaimer

This bot is for educational purposes only. Always test thoroughly on testnet before using real funds. Trading cryptocurrencies involves significant risk. 
