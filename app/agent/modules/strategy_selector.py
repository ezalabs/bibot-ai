from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.langgraph.state import TradingState
from app.strategies.factory import StrategyFactory
from app.utils.logging.logger import get_logger
from app.config.settings import load_config
from app.agent.tools.strategy_tools import StrategyTool
from app.core.trading_executor import TradingExecutor

logger = get_logger(__name__)

class StrategySelectorModule:
    """
    Strategy selection node for the trading agent.
    Evaluates and selects the most appropriate strategy for current market conditions.
    """
    
    def __init__(self, llm=None, executor=None):
        """
        Initialize the strategy selector module.
        
        Args:
            llm: Language model to use for analysis (created if not provided)
            executor: TradingExecutor instance to use for strategies (created if not provided)
        """
        self.executor = executor or TradingExecutor(load_config())
        self.strategy_factory = StrategyFactory()
        self.strategy_tool = StrategyTool(service_registry=self.executor.services)
        
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
        Select and apply the appropriate trading strategy.
        
        Args:
            state: Current trading state
            
        Returns:
            Updated trading state
        """
        try:
            logger.info("Running strategy selection...")
            
            # Get market data from state
            market_data = state.market_data
            
            if not market_data:
                logger.error("No market data available for strategy selection")
                state.strategy_params = {"error": "No market data available"}
                return state
            
            # Evaluate strategy suitability
            strategy_evaluation = self.strategy_tool.evaluate_strategy_suitability(market_data)
            
            # Get recommended strategy
            recommended_strategy = strategy_evaluation.get("recommended_strategy")
            
            # Generate signals using the recommended strategy
            signals_result = self.strategy_tool.generate_signals(recommended_strategy, market_data)
            
            # Get LLM evaluation of strategy and signals
            strategy_context = {
                "recommended_strategy": recommended_strategy,
                "reason": strategy_evaluation.get("reason", ""),
                "signals": signals_result.get("signals", {}),
                "market_analysis": state.analysis_results.get("llm_analysis", "")
            }
            
            strategy_prompt = [
                SystemMessage(content=(
                    "You are an expert trading strategy analyst. "
                    "Your task is to evaluate if the chosen trading strategy and signals align with the market analysis. "
                    "Provide a concise assessment of whether the strategy and signals make sense given the current market conditions. "
                    "Suggest improvements if appropriate. Be specific and actionable."
                )),
                HumanMessage(content=(
                    f"Please evaluate the following trading strategy and signals:\n\n"
                    f"Recommended Strategy: {strategy_context['recommended_strategy']}\n"
                    f"Reason: {strategy_context['reason']}\n"
                    f"Trading Signals: Long = {strategy_context['signals'].get('long', False)}, "
                    f"Short = {strategy_context['signals'].get('short', False)}\n\n"
                    f"Based on this market analysis:\n{strategy_context['market_analysis']}"
                ))
            ]
            
            llm_response = self.llm.invoke(strategy_prompt)
            
            # Update state with strategy information
            state.selected_strategy = recommended_strategy
            state.strategy_params = {
                "details": signals_result,
                "evaluation": strategy_evaluation,
                "llm_assessment": llm_response.content,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update trading signals
            state.trading_signals = signals_result.get("signals", {"long": False, "short": False})
            
            # Update last_updated timestamp
            state.last_updated = datetime.now()
            
            logger.info(f"Strategy selection completed. Selected strategy: {recommended_strategy}")
            logger.info(f"Trading signals: Long = {state.trading_signals.get('long', False)}, Short = {state.trading_signals.get('short', False)}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in strategy selection: {e}")
            
            # Update state with error information
            state.strategy_params = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            state.trading_signals = {"long": False, "short": False}
            
            return state 