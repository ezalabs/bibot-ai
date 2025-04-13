from typing import Dict, Any
from datetime import datetime
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.langgraph.state import TradingState
from app.agent.tools.risk_tools import RiskTool
from app.utils.logging.logger import get_logger
from app.config.settings import load_config

logger = get_logger(__name__)

class RiskAnalyzerModule:
    """
    Risk analysis module for the trading agent.
    Analyzes risk based on market data and trading signals.
    """
    
    def __init__(self, llm=None):
        """Initialize the risk analyzer module."""
        self.risk_tool = RiskTool()
        if llm:
            self.llm = llm
        else:
            config = load_config()
            self.llm = ChatOpenAI(
                model=config.llm.model_name, 
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens
            )
    
    def __call__(self, state: TradingState) -> TradingState:
        """
        Analyze risk profile of potential trades and update the state.
        
        Args:
            state: Current trading state
            
        Returns:
            Updated trading state
        """
        try:
            logger.info("Running risk analysis...")
            
            # Get market data and trading signals from state
            market_data = state.market_data
            trading_signals = state.trading_signals
            
            if not market_data:
                logger.error("No market data available for risk analysis")
                state.risk_assessment = {
                    "level": "unknown",
                    "assessment": "NOT_FAVORABLE",
                    "reason": "No market data available for analysis",
                    "timestamp": datetime.now().isoformat()
                }
                return state
            
            if not trading_signals:
                logger.info("No trading signals available, skipping risk analysis")
                state.risk_assessment = {
                    "level": "none",
                    "assessment": "NOT_FAVORABLE",
                    "reason": "No trading signals to analyze",
                    "timestamp": datetime.now().isoformat()
                }
                return state
            
            # Check if any signals are active
            has_active_signal = trading_signals.get("long", False) or trading_signals.get("short", False)
            
            if not has_active_signal:
                logger.info("No active trading signals, skipping detailed risk analysis")
                state.risk_assessment = {
                    "level": "none",
                    "assessment": "NOT_FAVORABLE",
                    "reason": "No active trading signals",
                    "timestamp": datetime.now().isoformat()
                }
                return state
            
            # Use LLM to analyze risk
            market_summary = market_data.get("market_summary", {})
            sentiment = market_data.get("sentiment", {})
            strategy_params = state.strategy_params or {}
            llm_analysis = state.analysis_results.get("llm_analysis", "")
            
            # Prepare context for risk assessment
            risk_context = {
                "market_conditions": {
                    "current_price": market_summary.get("current_price", "unknown"),
                    "volatility": sentiment.get("volatility", "unknown"),
                    "market_trend": sentiment.get("price_trend", "unknown"),
                    "overall_sentiment": sentiment.get("overall_sentiment", "unknown")
                },
                "trading_signals": {
                    "long": trading_signals.get("long", False),
                    "short": trading_signals.get("short", False)
                },
                "strategy": {
                    "name": state.selected_strategy,
                    "params": strategy_params
                },
                "market_analysis": llm_analysis
            }
            
            # Get analysis from LLM
            risk_prompt = [
                SystemMessage(content=(
                    "You are an expert risk management analyst for cryptocurrency trading. "
                    "Your task is to analyze the risk level of a potential trade based on market conditions and signals. "
                    "Provide a concise risk assessment with a risk level (high, medium, low, or none) and a clear recommendation. "
                    "Be specific about why the trade is or is not favorable."
                )),
                HumanMessage(content=(
                    f"Please assess the risk level of this potential trade:\n\n"
                    f"Market Conditions:\n"
                    f"- Current Price: {risk_context['market_conditions']['current_price']}\n"
                    f"- Volatility: {risk_context['market_conditions']['volatility']}\n"
                    f"- Market Trend: {risk_context['market_conditions']['market_trend']}\n"
                    f"- Overall Sentiment: {risk_context['market_conditions']['overall_sentiment']}\n\n"
                    f"Trading Signals:\n"
                    f"- Long Signal: {risk_context['trading_signals']['long']}\n"
                    f"- Short Signal: {risk_context['trading_signals']['short']}\n\n"
                    f"Strategy: {risk_context['strategy']['name']}\n\n"
                    f"Market Analysis: {risk_context['market_analysis']}\n\n"
                    f"Provide your risk assessment in this format:\n"
                    f"Risk Level: [high/medium/low/none]\n"
                    f"Assessment: [FAVORABLE/NOT_FAVORABLE]\n"
                    f"Reason: [your detailed reasoning]"
                ))
            ]
            
            llm_response = self.llm.invoke(risk_prompt)
            
            # Extract risk level and assessment from response
            response_text = llm_response.content
            
            # Parse risk level
            risk_level_match = re.search(r"Risk Level:\s*(\w+)", response_text, re.IGNORECASE)
            risk_level = risk_level_match.group(1).lower() if risk_level_match else "unknown"
            
            # Parse assessment
            assessment_match = re.search(r"Assessment:\s*(\w+)", response_text, re.IGNORECASE)
            assessment = assessment_match.group(1).upper() if assessment_match else "NOT_FAVORABLE"
            
            # Parse reason
            reason_match = re.search(r"Reason:\s*(.*?)(?=$|\n\n)", response_text, re.IGNORECASE | re.DOTALL)
            reason = reason_match.group(1).strip() if reason_match else "No clear reasoning provided"
            
            # Set default assessment to NOT_FAVORABLE if no clear signal
            if assessment not in ["FAVORABLE", "NOT_FAVORABLE"]:
                assessment = "NOT_FAVORABLE"
            
            # Update state with risk assessment
            state.risk_assessment = {
                "level": risk_level,
                "assessment": assessment,
                "reason": reason,
                "full_analysis": response_text,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Risk analysis completed. Level: {risk_level}, Assessment: {assessment}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in risk analysis: {e}")
            
            # Update state with error information
            state.risk_assessment = {
                "level": "unknown",
                "assessment": "NOT_FAVORABLE",
                "reason": f"Error during risk analysis: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
            return state
    
    def should_execute_trade(self, state: TradingState) -> Dict[str, Any]:
        """
        Determine if a trade should be executed based on risk assessment.
        
        Args:
            state: Current trading state
            
        Returns:
            Dictionary with decision information
        """
        # Get risk assessment
        risk_assessment = state.risk_assessment
        
        # Default to no execution
        result = {"should_execute": False, "reason": "No risk assessment available"}
        
        if not risk_assessment:
            return result
        
        # Check for errors
        if "error" in risk_assessment:
            result["reason"] = f"Error in risk assessment: {risk_assessment['error']}"
            return result
        
        # Check if there's a trade opportunity
        if not risk_assessment.get("trade_opportunity", False):
            result["reason"] = "No trade opportunity identified"
            return result
        
        # Check if the trade is favorable
        if not risk_assessment.get("favorable_trade", False):
            result["reason"] = "Trade not favorable based on risk assessment"
            return result
        
        # All checks passed, should execute
        return {
            "should_execute": True,
            "side": risk_assessment.get("side", "unknown"),
            "position_size": risk_assessment.get("position_sizing", {}).get("recommended_position_size"),
            "reason": "Trade meets risk criteria"
        }
    
    def _check_safety_limits(self, state: TradingState) -> bool:
        """
        Check if a trade would exceed safety limits.
        
        Args:
            state: Current trading state
            
        Returns:
            True if safety limits are respected, False otherwise
        """
        # Get configuration from risk_tool
        config = self.risk_tool.config
        
        # Check trade size limits
        max_position_size = getattr(config.trading, 'max_position_size', 0.25)
        
        # Check drawdown limits
        max_drawdown = getattr(config.trading, 'max_drawdown', 0.10)
        
        # Check market volatility
        market_data = state.market_data or {}
        market_summary = market_data.get('market_summary', {})
        sentiment = market_data.get('sentiment', {})
        
        volatility = sentiment.get('volatility', 0.0)
        max_volatility = getattr(config.trading, 'max_volatility', 3.0)
        
        # Return False if any safety limit would be exceeded
        if volatility > max_volatility:
            logger.warning(f"Safety limit exceeded: volatility {volatility} > {max_volatility}")
            return False
        
        # Add more safety checks as needed
        
        return True 