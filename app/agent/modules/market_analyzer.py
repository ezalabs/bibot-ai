from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.langgraph.state import TradingState
from app.agent.tools.market_tools import MarketDataTool
from app.utils.logging.logger import get_logger
from app.config.settings import load_config
from app.core.market_data import MarketData

logger = get_logger(__name__)

class MarketAnalyzerModule:
    """
    Market analysis node for the trading agent.
    Fetches market data and provides AI-powered analysis.
    """
    
    def __init__(self, llm=None, service_registry=None, market_data=None):
        """
        Initialize the market analyzer module.
        
        Args:
            llm: Language model for analysis (created if not provided)
            service_registry: Service registry to use
            market_data: Direct market data service (highest priority)
        """
        config = load_config()
        
        # Set up service access
        self.services = service_registry
        self._market_data = market_data
        
        # Initialize the market data tool
        self.market_data_tool = MarketDataTool(
            service_registry=service_registry,
            market_data=market_data
        )
        
        # Set up LLM
        if llm:
            self.llm = llm
        else:
            self.llm = ChatOpenAI(
                model=config.llm.model_name, 
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens
            )
    
    def __call__(self, state: TradingState) -> TradingState:
        """
        Process the market data and update the state.
        
        Args:
            state: Current trading state
            
        Returns:
            Updated trading state
        """
        try:
            logger.info("Running market analysis...")
            
            # Fetch market data
            market_data = self.market_data_tool.get_market_data()
            
            # Update state with raw market data
            state.market_data = market_data
            
            # Convert raw data to dataframe for sentiment analysis
            raw_data = market_data.get("raw_data", {})
            if raw_data:
                import pandas as pd
                df = pd.DataFrame(raw_data)
                sentiment_data = self.market_data_tool.analyze_market_sentiment(df)
                market_data["sentiment"] = sentiment_data
            
            # Use LLM to interpret the market data
            market_summary = market_data.get("market_summary", {})
            sentiment = market_data.get("sentiment", {})
            
            # Prepare market context for LLM analysis
            market_context = (
                f"Trading Pair: {market_summary.get('trading_pair', 'unknown')}\n"
                f"Current Price: {market_summary.get('current_price', 'unknown')}\n"
                f"Price Change (24h): {market_summary.get('price_change_24h', 'unknown')}%\n"
                f"Price High (24h): {market_summary.get('price_high_24h', 'unknown')}\n"
                f"Price Low (24h): {market_summary.get('price_low_24h', 'unknown')}\n"
                f"Volume Trend: {market_summary.get('volume_data', {}).get('volume_trend', 'unknown')}\n"
                f"Price Trend: {sentiment.get('price_trend', 'unknown')}\n"
                f"Volatility: {sentiment.get('volatility', 'unknown')}\n"
                f"Overall Sentiment: {sentiment.get('overall_sentiment', 'unknown')}\n"
            )
            
            # Get LLM interpretation
            analysis_prompt = [
                SystemMessage(content=(
                    "You are an expert cryptocurrency market analyst. "
                    "Your task is to analyze the current market data and provide insights. "
                    "Focus on identifying important patterns and making actionable observations. "
                    "Be concise and direct. Identify if the market conditions appear favorable for trading."
                )),
                HumanMessage(content=f"Please analyze this market data:\n\n{market_context}")
            ]
            
            llm_response = self.llm.invoke(analysis_prompt)
            
            # Update state with analysis results
            state.analysis_results = {
                "market_data": market_data,
                "llm_analysis": llm_response.content,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update last_updated timestamp
            state.last_updated = datetime.now()
            
            logger.info("Market analysis completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            
            # Update state with error information
            state.analysis_results = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return state 