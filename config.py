from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Trading Parameters ---------------------------------------------------------------------

TRADING_PAIR = 'BTCUSDT'  # Trading pair
# This defines what you're trading: Bitcoin (BTC) against Tether (USDC)
# You could change this to other pairs like 'ETHUSDT' for Ethereum or 'SOLUSDT' for Solana

POSITION_SIZE = 0.01  # Position size in BTC
# This means each trade will involve 0.01 BTC
# At current prices (~$65,000/BTC), this would be approximately $650 per position
# This is a relatively conservative position size for risk management

LEVERAGE = 5  # Leverage for futures trading
# 5x leverage means you can control 5 times more assets than your capital
# Example: With $1,000, you can open positions worth $5,000
# Higher leverage = higher potential profits but also higher risk
# 5x is considered moderate leverage (Binance offers up to 125x)

# Scalping Parameters
TAKE_PROFIT_PERCENTAGE = 0.1  # 0.1% take profit
# The bot will close positions when profit reaches 0.1%
# With 5x leverage, this translates to 0.5% return on investment
# Example: $1,000 position → $1,005 (before fees)
# This is a typical target for scalping strategy (small, quick profits)

STOP_LOSS_PERCENTAGE = 0.05   # 0.05% stop loss
# Positions will be closed if losses reach 0.05%
# With 5x leverage, this means 0.25% loss on investment
# Example: $1,000 position → $997.50 (before fees)
# The stop loss is tighter than take profit (2:1 risk-reward ratio)

MAX_POSITIONS = 3  # Maximum number of concurrent positions
# Bot can have up to 3 open trades at once
# This helps distribute risk across multiple opportunities
# Also prevents overexposure to the market

# Technical Analysis Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
# RSI (Relative Strength Index) measures momentum
# 14 periods is the standard setting
# Above 70 = potentially overbought (sell signal)
# Below 30 = potentially oversold (buy signal)
# These are conservative thresholds (some use 80/20)

EMA_FAST = 9
EMA_SLOW = 21
# EMA (Exponential Moving Average) tracks trend
# Fast EMA (9 periods) reacts quickly to price changes
# Slow EMA (21 periods) shows longer-term trend
# When fast crosses above slow = potential buy signal
# When fast crosses below slow = potential sell signal

# Testnet Configuration
USE_TESTNET = True  # Set to False for live trading
TESTNET_URL = 'https://testnet.binance.vision'