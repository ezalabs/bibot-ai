from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Trading Parameters 

TRADING_PAIR = 'BTCUSDT'
POSITION_SIZE = 0.01  
LEVERAGE = 5
TAKE_PROFIT_PERCENTAGE = 0.1
STOP_LOSS_PERCENTAGE = 0.05  
MAX_POSITIONS = 3  # Maximum number of concurrent positions

# Technical Analysis Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

EMA_FAST = 9
EMA_SLOW = 21

# Testnet Configuration
USE_TESTNET = True  # Set to False for live trading
TESTNET_URL = 'https://testnet.binance.vision'