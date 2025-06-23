import streamlit as st
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage

class TokenUsageTracker(BaseCallbackHandler):
    """LLM-agnostic token usage and cost tracker"""
    
    # Model pricing per 1K tokens (input/output) - Updated 2024 rates
    MODEL_PRICING = {
        # Google Gemini models
        "gemini-1.5-flash": {"input": 0.00015, "output": 0.0006},  # $0.15/$0.60 per 1M tokens
        "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},    # $3.50/$10.50 per 1M tokens
        "gemini-pro": {"input": 0.0005, "output": 0.0015},        # Legacy pricing
        
        # OpenAI models (for future multi-model support)
        "gpt-4o": {"input": 0.005, "output": 0.015},              # $5.00/$15.00 per 1M tokens
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},      # $0.15/$0.60 per 1M tokens
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},     # $0.50/$1.50 per 1M tokens
        
        # Anthropic models (for future multi-model support)
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},   # $3.00/$15.00 per 1M tokens
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},  # $0.25/$1.25 per 1M tokens
    }
    
    def __init__(self):
        super().__init__()
        # Initialize session state for tracking
        if 'token_usage' not in st.session_state:
            st.session_state.token_usage = {
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_cost': 0.0,
                'query_count': 0,
                'model_usage': {},
                'session_start': datetime.now().isoformat(),
                'detailed_calls': []
            }
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts"""
        self.start_time = time.time()
        
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM ends - extract token usage"""
        end_time = time.time()
        response_time = end_time - getattr(self, 'start_time', end_time)
        
        # Extract token usage from response
        token_info = self._extract_token_usage(response, response_time)
        if token_info:
            self._update_session_stats(token_info)
    
    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs) -> None:
        """Called when chat model starts"""
        self.start_time = time.time()
        
    def on_chat_model_end(self, response: LLMResult, **kwargs) -> None:
        """Called when chat model ends"""
        end_time = time.time()
        response_time = end_time - getattr(self, 'start_time', end_time)
        
        # Extract token usage from response
        token_info = self._extract_token_usage(response, response_time)
        if token_info:
            self._update_session_stats(token_info)
        
    def _extract_token_usage(self, response: LLMResult, response_time: float) -> Optional[Dict]:
        """Extract token usage from LLM response"""
        try:
            # Try to get usage metadata from response
            if hasattr(response, 'llm_output') and response.llm_output:
                usage = response.llm_output.get('usage', {})
                if usage:
                    return {
                        'input_tokens': usage.get('prompt_tokens', 0),
                        'output_tokens': usage.get('completion_tokens', 0),
                        'total_tokens': usage.get('total_tokens', 0),
                        'model': response.llm_output.get('model_name', 'unknown'),
                        'response_time': response_time,
                        'timestamp': datetime.now().isoformat()
                    }
            
            # For Google Gemini, try alternative extraction methods
            for generation in response.generations:
                for gen in generation:
                    if hasattr(gen, 'generation_info') and gen.generation_info:
                        usage = gen.generation_info.get('usage_metadata', {})
                        if usage:
                            return {
                                'input_tokens': usage.get('prompt_token_count', 0),
                                'output_tokens': usage.get('candidates_token_count', 0),
                                'total_tokens': usage.get('total_token_count', 0),
                                'model': 'gemini-2.0-flash-exp',  # Match current model
                                'response_time': response_time,
                                'timestamp': datetime.now().isoformat()
                            }
            
            # Fallback: estimate tokens if no usage data available
            return self._estimate_token_usage(response, response_time)
            
        except Exception as e:
            return self._estimate_token_usage(response, response_time)
    
    def _estimate_token_usage(self, response: LLMResult, response_time: float) -> Dict:
        """Estimate token usage when exact counts aren't available"""
        # Rough estimation: ~4 characters per token for English text
        total_chars = 0
        for generation in response.generations:
            for gen in generation:
                total_chars += len(gen.text)
        
        estimated_output_tokens = max(1, total_chars // 4)
        estimated_input_tokens = max(1, estimated_output_tokens // 3)  # Rough ratio
        
        return {
            'input_tokens': estimated_input_tokens,
            'output_tokens': estimated_output_tokens,
            'total_tokens': estimated_input_tokens + estimated_output_tokens,
            'model': 'gemini-1.5-flash',  # Default model
            'response_time': response_time,
            'timestamp': datetime.now().isoformat(),
            'estimated': True
        }
    
    def _update_session_stats(self, token_info: Dict):
        """Update session statistics with new token usage"""
        stats = st.session_state.token_usage
        
        # Update totals
        stats['total_input_tokens'] += token_info['input_tokens']
        stats['total_output_tokens'] += token_info['output_tokens']
        stats['query_count'] += 1
        
        # Calculate cost
        model = token_info['model']
        if 'cost' in token_info:
            # Pre-calculated cost (e.g., for function calls)
            cost = token_info['cost']
        else:
            # Calculate cost from tokens
            cost = self._calculate_cost(
                token_info['input_tokens'], 
                token_info['output_tokens'], 
                model
            )
        stats['total_cost'] += cost
        token_info['cost'] = cost
        
        # Update model usage stats
        if model not in stats['model_usage']:
            stats['model_usage'][model] = {
                'calls': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'cost': 0.0
            }
        
        model_stats = stats['model_usage'][model]
        model_stats['calls'] += 1
        model_stats['input_tokens'] += token_info['input_tokens']
        model_stats['output_tokens'] += token_info['output_tokens']
        model_stats['cost'] += cost
        
        # Store detailed call info (keep last 50)
        stats['detailed_calls'].append(token_info)
        if len(stats['detailed_calls']) > 50:
            stats['detailed_calls'].pop(0)
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate cost based on token usage and model pricing"""
        # Normalize model name for pricing lookup
        model_key = self._normalize_model_name(model)
        
        if model_key not in self.MODEL_PRICING:
            # Use default Gemini pricing for unknown models
            model_key = "gemini-1.5-flash"
        
        pricing = self.MODEL_PRICING[model_key]
        
        # Convert per-1K pricing to per-token
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        
        return input_cost + output_cost
    
    def _normalize_model_name(self, model: str) -> str:
        """Normalize model name for pricing lookup"""
        model_lower = model.lower()
        
        # Map various model name formats to pricing keys
        if 'gemini-1.5-flash' in model_lower or 'flash' in model_lower:
            return 'gemini-1.5-flash'
        elif 'gemini-1.5-pro' in model_lower:
            return 'gemini-1.5-pro'
        elif 'gemini' in model_lower:
            return 'gemini-pro'
        elif 'gpt-4o-mini' in model_lower:
            return 'gpt-4o-mini'
        elif 'gpt-4o' in model_lower:
            return 'gpt-4o'
        elif 'gpt-3.5' in model_lower:
            return 'gpt-3.5-turbo'
        elif 'claude-3-5-sonnet' in model_lower:
            return 'claude-3-5-sonnet'
        elif 'claude-3-haiku' in model_lower:
            return 'claude-3-haiku'
        
        return 'gemini-1.5-flash'  # Default fallback
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        return st.session_state.token_usage.copy()
    
    def reset_session_stats(self):
        """Reset session statistics"""
        st.session_state.token_usage = {
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0,
            'query_count': 0,
            'model_usage': {},
            'session_start': datetime.now().isoformat(),
            'detailed_calls': []
        }

# Global token tracker instance
token_tracker = TokenUsageTracker()

def track_tokens(func):
    """Decorator to add token tracking to functions"""
    def wrapper(*args, **kwargs):
        # Add callback to kwargs if supported
        if 'callbacks' in kwargs:
            if not isinstance(kwargs['callbacks'], list):
                kwargs['callbacks'] = []
            kwargs['callbacks'].append(token_tracker)
        else:
            kwargs['callbacks'] = [token_tracker]
        
        return func(*args, **kwargs)
    return wrapper