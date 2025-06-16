# src/monitoring.py - Updated LangSmith integration
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from langsmith import Client, traceable
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

class SalesforceMonitor:
    def __init__(self):
        self.client = None
        self.setup_langsmith()
        self.setup_logging()
        
        # Metrics tracking
        self.query_count = 0
        self.error_count = 0
        self.function_call_count = 0
        self.response_times = []
    
    def setup_langsmith(self):
        """Setup LangSmith tracing with latest SDK"""
        try:
            # Updated environment variable names and API key format
            api_key = os.getenv("LANGSMITH_API_KEY")
            if api_key:
                os.environ["LANGSMITH_TRACING"] = "true"
                
                self.client = Client(
                    api_key=api_key,
                    api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
                )
                
                # Set project name
                project_name = os.getenv("LANGSMITH_PROJECT", "salesforce-advisor")
                os.environ["LANGSMITH_PROJECT"] = project_name
                
                print("✅ LangSmith monitoring enabled")
            else:
                print("⚠️ LANGSMITH_API_KEY not found - monitoring disabled")
                print("   Set LANGSMITH_API_KEY environment variable")
        except Exception as e:
            print(f"❌ LangSmith setup failed: {e}")
    
    def setup_logging(self):
        """Setup structured logging"""
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/salesforce_advisor.log'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('SalesforceAdvisor')
    
    @traceable(name="salesforce_query_log")
    def log_query(self, question: str, response_time: float, 
                  sources_count: int, tool_used: Optional[str] = None,
                  error: Optional[str] = None, model_used: Optional[str] = None):
        """Log query with detailed metrics using traceable decorator"""
        self.query_count += 1
        
        if error:
            self.error_count += 1
            self.logger.error(f"Query failed: {question[:100]}... Error: {error}")
        else:
            self.response_times.append(response_time)
            self.logger.info(
                f"Query processed - "
                f"Question: {question[:50]}... | "
                f"Response time: {response_time:.2f}s | "
                f"Sources: {sources_count} | "
                f"Tool used: {tool_used or 'None'} | "
                f"Model: {model_used or 'gemini'}"
            )
            
            if tool_used:
                self.function_call_count += 1
        
        # Return structured data for LangSmith tracing
        return {
            "question": question,
            "response_time": response_time,
            "sources_count": sources_count,
            "tool_used": tool_used,
            "model_used": model_used,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "success": error is None
        }
    
    def log_run(self, run_name: str, inputs: Dict[str, Any], 
                outputs: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Log custom runs to LangSmith"""
        if self.client:
            try:
                run = self.client.create_run(
                    name=run_name,
                    inputs=inputs,
                    outputs=outputs,
                    run_type="chain",
                    extra=metadata or {}
                )
                return run
            except Exception as e:
                self.logger.warning(f"Failed to send run to LangSmith: {e}")
        return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return {
            "total_queries": self.query_count,
            "total_errors": self.error_count,
            "function_calls": self.function_call_count,
            "average_response_time": round(avg_response_time, 2),
            "error_rate": round((self.error_count / self.query_count * 100), 2) if self.query_count > 0 else 0,
            "uptime": "N/A"  # Can be enhanced with actual uptime tracking
        }
    
    @traceable(name="system_event")
    def log_system_event(self, event: str, details: Dict[str, Any]):
        """Log system events with tracing"""
        self.logger.info(f"System event: {event} - {details}")
        return {"event": event, "details": details, "timestamp": datetime.now().isoformat()}

# Global monitor instance
monitor = SalesforceMonitor()

def track_query(func):
    """Decorator to track query performance with LangSmith tracing"""
    @traceable(name=f"tracked_{func.__name__}")
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        error = None
        result = None
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error = str(e)
            raise
        finally:
            response_time = time.time() - start_time
            
            # Extract question from args (assuming it's the first arg after self)
            question = args[1] if len(args) > 1 else "Unknown"
            sources_count = len(result.get("sources", [])) if result else 0
            tool_used = result.get("tool_used") if result else None
            model_used = result.get("model_used", "gemini") if result else "gemini"
            
            monitor.log_query(question, response_time, sources_count, tool_used, error, model_used)
    
    return wrapper

# New: Gemini-specific tracing wrapper
def trace_gemini_call(func):
    """Specific decorator for Gemini API calls"""
    @traceable(name="gemini_api_call")
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            response_time = time.time() - start_time
            
            # Log the Gemini call details
            monitor.log_run(
                run_name="gemini_completion",
                inputs={
                    "prompt": str(args[1]) if len(args) > 1 else "Unknown",
                    "model": "gemini",
                    "function_name": func.__name__
                },
                outputs={
                    "response": str(result)[:500] if result else "None",
                    "response_time": response_time
                },
                metadata={
                    "provider": "google",
                    "model_family": "gemini",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return result
        except Exception as e:
            response_time = time.time() - start_time
            monitor.log_run(
                run_name="gemini_completion_error",
                inputs={
                    "prompt": str(args[1]) if len(args) > 1 else "Unknown",
                    "model": "gemini"
                },
                outputs={"error": str(e)},
                metadata={
                    "provider": "google",
                    "model_family": "gemini",
                    "response_time": response_time,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise
    
    return wrapper