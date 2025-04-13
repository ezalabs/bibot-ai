import re
from typing import Dict, Any, List
from datetime import datetime

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.models.langgraph.state import TradingState
from app.agent.modules.market_analyzer import MarketAnalyzerModule
from app.agent.modules.strategy_selector import StrategySelectorModule
from app.agent.modules.risk_analyzer import RiskAnalyzerModule
from app.agent.modules.executor import ExecutorModule
from app.registry import ServiceRegistry
from app.core.trading_executor import TradingExecutor
from app.config.settings import load_config, BiBotConfig
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)

class BiBotTradingAgent:
    """
    AI trading agent built with LangGraph.
    Integrates market analysis, strategy selection, risk assessment, 
    and trade execution in a coordinated workflow.
    """
    
    def __init__(
        self,
        config: BiBotConfig = None,
        llm: ChatOpenAI = None,
        trading_executor: TradingExecutor = None,
        service_registry: ServiceRegistry = None
    ):
        """
        Initialize the trading agent.
        
        Args:
            config: Configuration to use (defaults to loaded config)
            llm: Language model to use (created if not provided)
            trading_executor: TradingExecutor instance to use (created if not provided)
            service_registry: Service registry to use (created if not provided)
        """
        self.config = config or load_config()
        self.services = service_registry or ServiceRegistry()
        self.trading_executor = trading_executor or TradingExecutor(service_registry=self.services)
        
        if llm:
            self.llm = llm
        else:
            self.llm = ChatOpenAI(
                model=self.config.llm.model_name,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens
            )
        
        # Initialize modules with shared trading_executor
        self.analyzer = MarketAnalyzerModule(llm=self.llm)
        self.strategy_selector = StrategySelectorModule(llm=self.llm, executor=self.trading_executor)
        self.risk_assessor = RiskAnalyzerModule(llm=self.llm)
        self.executor = ExecutorModule(llm=self.llm, registry=self.services, trading_executor=self.trading_executor)
        
        logger.info("Trading agent initialized with shared TradingExecutor")
        
        # Build the workflow
        self.workflow = self.build_workflow()
    
    def build_workflow(self):
        """Build the LangGraph workflow."""
        # Define the workflow
        builder = StateGraph(TradingState)
        
        # Add all nodes
        builder.add_node("market_analyzer", self.analyzer)
        builder.add_node("strategy_selector", self.strategy_selector)
        builder.add_node("risk_analyzer", self.risk_assessor)
        builder.add_node("executor", self.executor)
        
        # Add edges
        builder.add_edge("market_analyzer", "strategy_selector")
        builder.add_edge("strategy_selector", "risk_analyzer")
        
        # Conditional edges from risk analyzer
        builder.add_conditional_edges(
            "risk_analyzer",
            self._risk_router
        )
        
        # Set the entry point
        builder.set_entry_point("market_analyzer")
        
        # Compile the workflow
        return builder.compile()
    
    def _risk_router(self, state: TradingState):
        """Route to next node based on risk assessment."""
        # Check if the risk assessment is favorable
        assessment = state.risk_assessment.get("assessment", "NOT_FAVORABLE")
        
        if assessment == "FAVORABLE":
            # If favorable, go to executor
            return "executor"
        else:
            # If not favorable, end the workflow
            # Update execution_status with the reason from risk_assessment
            reason = state.risk_assessment.get("reason", "Risk assessment not favorable")
            state.execution_status = {
                "executed": False,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            return END
    
    def run(self) -> TradingState:
        """
        Run the trading agent workflow once.
        
        Returns:
            Final trading state
        """
        logger.info("Starting trading agent run...")
        
        # Create initial state
        initial_state = TradingState()
        
        # Create thread config for persistence
        thread_id = f"trading-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Simple invocation with config
        result = self.workflow.invoke(initial_state, config=config)
        
        # Create a manual state to return with the important information preserved
        final_state = TradingState()
        
        # Copy analysis results
        if hasattr(result, 'analysis_results'):
            final_state.analysis_results = result.analysis_results
        
        # Copy strategy information
        if hasattr(result, 'selected_strategy'):
            final_state.selected_strategy = result.selected_strategy
        if hasattr(result, 'strategy_params'):
            final_state.strategy_params = result.strategy_params
        if hasattr(result, 'trading_signals'):
            final_state.trading_signals = result.trading_signals
        
        # Copy risk assessment
        if hasattr(result, 'risk_assessment'):
            final_state.risk_assessment = result.risk_assessment
            # If execution_status is not set but risk_assessment contains reason, copy it
            if not hasattr(result, 'execution_status') and 'reason' in result.risk_assessment:
                final_state.execution_status = {
                    "executed": False,
                    "reason": result.risk_assessment['reason'],
                    "timestamp": datetime.now().isoformat()
                }
        
        # Copy execution status
        if hasattr(result, 'execution_status'):
            final_state.execution_status = result.execution_status
        
        logger.info("Trading agent run completed")
        
        return final_state
    
    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get history of trading agent runs.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of trading run history records
        """
        # No persistent checkpoints yet, so we just return an empty list
        return []
    
    def cleanup(self):
        """Clean up all positions and connections."""
        try:
            # Clean up all positions
            self.trading_executor.cleanup_all_positions()
            
            # Close client connection if available
            client = self.services.client
            if hasattr(client, 'close_connection'):
                client.close_connection()
                logger.info("Connection closed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise 