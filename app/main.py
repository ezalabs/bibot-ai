#!/usr/bin/env python
import argparse
import signal
import time

from app.agent.agent import BiBotTradingAgent
from app.config.settings import load_config
from app.core.trading_executor import TradingExecutor
from app.registry import ServiceRegistry
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)

# Flag to track if the app is running
running = True

def signal_handler(sig, frame):
    """Handle signals to gracefully exit."""
    global running
    logger.info("Received shutdown signal, stopping...")
    running = False

def run_autonomous_agent(interval: int = 3600, cleanup: bool = False):
    """
    Run the trading agent autonomously at specified intervals.
    
    Args:
        interval: Interval between trading cycles in seconds
        cleanup: Whether to clean up existing positions on startup
    """
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    config = load_config()
    
    # Create shared services
    registry = ServiceRegistry()
    trading_executor = TradingExecutor(config=config, service_registry=registry)
    
    # Initialize BiBot
    agent = BiBotTradingAgent(
        config=config, 
        trading_executor=trading_executor,
        service_registry=registry
    )
    
    # Cleanup if requested
    if cleanup:
        try:
            logger.info("Cleaning up existing positions")
            agent.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return
    
    logger.info(f"Starting autonomous trading with {interval} second interval")
    print(f"Trading agent will run every {interval // 60} minutes")
    print(f"Using model: {config.llm.model_name}")
    print("Press Ctrl+C to stop\n")
    
    # Main execution loop
    while running:
        try:
            logger.info("Starting trading cycle")
            
            # Run the trading agent
            final_state = agent.run()
            
            # Process the results
            if hasattr(final_state, '__dict__'):
                state_dict = final_state.__dict__
            else:
                state_dict = final_state
                
            # Log generated trading signals
            trading_signals = state_dict.get('trading_signals', {})
            logger.info(f"Trading signals: {trading_signals}")
            
            # Determine if we should execute a trade
            should_execute = False
            
            # Check risk_assessment and strategy_params for favorable conditions
            risk_assessment = state_dict.get('risk_assessment', {}) or {}
            strategy_params = state_dict.get('strategy_params', {}) or {}
            
            if risk_assessment and risk_assessment.get('assessment') == 'FAVORABLE':
                should_execute = True
                logger.info("Risk assessment is favorable")
            elif strategy_params and strategy_params.get('confidence', 0) > 0.7:
                should_execute = True
                logger.info(f"Strategy confidence is high: {strategy_params.get('confidence')}")
            
            # Get execution results
            execution_status = state_dict.get('execution_status', {}) or {}
            
            # Log trade execution if performed
            if should_execute and execution_status.get('executed', False):
                logger.info(f"Trade executed: {execution_status}")
            else:
                reason = execution_status.get('reason', 'No favorable trading opportunity')
                logger.info(f"No trade executed: {reason}")
            
            # Wait for the next interval
            logger.info(f"Sleeping for {interval} seconds")
            
            # Sleep in small chunks to allow for graceful shutdown
            sleep_chunks = 10  # seconds per chunk
            for _ in range(interval // sleep_chunks):
                if not running:
                    break
                time.sleep(sleep_chunks)
                
            # Sleep any remaining time
            remaining_time = interval % sleep_chunks
            if remaining_time > 0 and running:
                time.sleep(remaining_time)
                
        except Exception as e:
            logger.error(f"Error in trading cycle: {str(e)}")
            # Sleep before retrying
            time.sleep(interval)
    
    # Cleanup before exit
    try:
        logger.info("Cleaning up resources")
        agent.cleanup()
    except Exception as e:
        logger.error(f"Error during final cleanup: {e}")
    
    logger.info("Trading agent stopped")

def main():
    """Parse command-line arguments and run the app."""
    parser = argparse.ArgumentParser(description="BiBot AI trading bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up tracked positions")
    parser.add_argument("--interval", type=int, default=3600, help="Trading interval in seconds")
    
    args = parser.parse_args()
    
    # Run the agent
    run_autonomous_agent(interval=args.interval, cleanup=args.cleanup)

if __name__ == "__main__":
    main()