from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.langgraph.state import TradingState
from app.agent.tools.execution_tools import ExecutionTool
from app.registry import ServiceRegistry
from app.utils.logging.logger import get_logger
from app.config.settings import load_config
from app.core.trading_executor import TradingExecutor

logger = get_logger(__name__)

class ExecutorModule:
    """
    Execution node for the trading agent.
    Responsible for executing trades based on strategy signals and risk assessment.
    """
    
    def __init__(self, llm=None, registry: ServiceRegistry = None, trading_executor: TradingExecutor = None):
        """
        Initialize the executor module.
        
        Args:
            llm: Language model to use for analysis (created if not provided)
            registry: Service registry to use for trade execution
            trading_executor: TradingExecutor instance to use (created if not provided)
        """
        self.registry = registry
        # Use provided trading_executor or create a new one
        self.trading_executor = trading_executor or TradingExecutor(service_registry=registry)
        self.execution_tool = ExecutionTool(trading_executor=self.trading_executor)
        
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
        Execute trades based on state information.
        
        Args:
            state: Current trading state
            
        Returns:
            Updated trading state
        """
        try:
            logger.info("Running trade execution...")
            
            # Get required data from state
            risk_assessment = state.risk_assessment
            trading_signals = state.trading_signals
            
            if not risk_assessment or not trading_signals:
                logger.error("Missing required data for trade execution")
                state.execution_status = {"error": "Missing required data"}
                return state
            
            # Check if position limit reached
            position_check = self.execution_tool.check_position_limit()
            if position_check["limit_reached"]:
                logger.info("Maximum position limit reached, no new trades will be executed")
                state.execution_status = {
                    "executed": False,
                    "reason": "Maximum position limit reached",
                    "position_info": position_check,
                    "timestamp": datetime.now().isoformat()
                }
                return state
            
            # Check if there are any active signals
            if not trading_signals.get("long", False) and not trading_signals.get("short", False):
                logger.info("No active trading signals, no trades will be executed")
                state.execution_status = {
                    "executed": False,
                    "reason": "No active trading signals",
                    "timestamp": datetime.now().isoformat()
                }
                return state
            
            # Check if trade is favorable based on risk assessment
            if not risk_assessment.get("favorable_trade", False):
                logger.info("Trade not favorable based on risk assessment, no trades will be executed")
                state.execution_status = {
                    "executed": False,
                    "reason": "Trade not favorable based on risk assessment",
                    "risk_level": risk_assessment.get("risk_level", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }
                return state
            
            # Get the recommended position size from risk assessment
            position_size = None
            if "position_sizing" in risk_assessment:
                position_size = risk_assessment["position_sizing"].get("recommended_position_size")
            
            # Execute trade based on signals
            if trading_signals.get("long", False):
                # Execute long trade
                execution_result = self.execution_tool.execute_long_trade(position_size)
                
                # Update state with execution result
                state.execution_status = {
                    "executed": execution_result.get("success", False),
                    "side": "long",
                    "position": execution_result.get("position"),
                    "message": execution_result.get("message"),
                    "error": execution_result.get("error"),
                    "timestamp": datetime.now().isoformat()
                }
                
                # If successful, add to trading history
                if execution_result.get("success", False):
                    trade_record = {
                        "timestamp": datetime.now().isoformat(),
                        "side": "long",
                        "position": execution_result.get("position"),
                        "strategy": state.selected_strategy,
                        "market_context": state.analysis_results.get("llm_analysis"),
                        "risk_assessment": risk_assessment
                    }
                    state.trading_history.append(trade_record)
                    
                    logger.info(f"Successfully executed long trade at price: {execution_result.get('position', {}).get('entry_price', 'unknown')}")
                else:
                    logger.error(f"Failed to execute long trade: {execution_result.get('error', 'unknown error')}")
                
            elif trading_signals.get("short", False):
                # Execute short trade
                execution_result = self.execution_tool.execute_short_trade(position_size)
                
                # Update state with execution result
                state.execution_status = {
                    "executed": execution_result.get("success", False),
                    "side": "short",
                    "position": execution_result.get("position"),
                    "message": execution_result.get("message"),
                    "error": execution_result.get("error"),
                    "timestamp": datetime.now().isoformat()
                }
                
                # If successful, add to trading history
                if execution_result.get("success", False):
                    trade_record = {
                        "timestamp": datetime.now().isoformat(),
                        "side": "short",
                        "position": execution_result.get("position"),
                        "strategy": state.selected_strategy,
                        "market_context": state.analysis_results.get("llm_analysis"),
                        "risk_assessment": risk_assessment
                    }
                    state.trading_history.append(trade_record)
                    
                    logger.info(f"Successfully executed short trade at price: {execution_result.get('position', {}).get('entry_price', 'unknown')}")
                else:
                    logger.error(f"Failed to execute short trade: {execution_result.get('error', 'unknown error')}")
            
            # Get LLM summary of execution
            if state.execution_status.get("executed", False):
                execution_prompt = [
                    SystemMessage(content=(
                        "You are an expert trading execution analyst. "
                        "Your task is to provide a brief summary of the executed trade. "
                        "Be concise and focus on the key details of the execution, including "
                        "the reasons for entering the trade and expectations for its outcome."
                    )),
                    HumanMessage(content=(
                        f"Please provide a brief summary of the following trade execution:\n\n"
                        f"Side: {state.execution_status.get('side', 'unknown')}\n"
                        f"Entry Price: {state.execution_status.get('position', {}).get('entry_price', 'unknown')}\n"
                        f"Position Size: {state.execution_status.get('position', {}).get('quantity', 'unknown')}\n"
                        f"Strategy: {state.selected_strategy}\n\n"
                        f"Based on this market analysis:\n{state.analysis_results.get('llm_analysis', '')}\n\n"
                        f"And risk assessment:\n{risk_assessment.get('llm_assessment', '')}"
                    ))
                ]
                
                llm_response = self.llm.invoke(execution_prompt)
                
                # Add LLM summary to execution status
                state.execution_status["llm_summary"] = llm_response.content
            
            # Update last_updated timestamp
            state.last_updated = datetime.now()
            
            logger.info("Trade execution completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in trade execution: {e}")
            
            # Update state with error information
            state.execution_status = {
                "executed": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return state 