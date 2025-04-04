#!/usr/bin/env python
import argparse
import signal
import sys
from app.utils.logger import get_logger
from app.core.bibot import BiBot

# Configure logging
logger = get_logger()

# Create a global bot variable
bot = None

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    """Handle shutdown signals by saving state before exit"""
    logger.info("Shutdown signal received, saving state...")
    global bot
    if bot and hasattr(bot, '_save_positions_to_cache'):
        bot._save_positions_to_cache()
    logger.info("State saved, exiting")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Handle termination signal

def main():
    parser = argparse.ArgumentParser(description='BiBot - Binance Futures Trading Bot')
    parser.add_argument('--cleanup', action='store_true', help='Clean up all tracked positions and exit')
    args = parser.parse_args()
    
    global bot
    bot = BiBot()
    
    if args.cleanup:
        bot.cleanup_all_positions()
        logger.info("Cleanup completed, exiting")
        sys.exit(0)
    
    bot.run()

if __name__ == "__main__":
    main()