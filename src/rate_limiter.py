import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Any
from functools import wraps
import streamlit as st

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(deque)  # user_id -> deque of request timestamps
        self.lock = threading.Lock()
        
        # Rate limits (requests per time window)
        self.limits = {
            "queries_per_minute": 10,
            "queries_per_hour": 100,
            "function_calls_per_minute": 5,
            "function_calls_per_hour": 30
        }
    
    def get_user_id(self) -> str:
        """Get user identifier (use session state or IP)"""
        if hasattr(st, 'session_state') and hasattr(st.session_state, 'user_id'):
            return st.session_state.user_id
        
        # Fallback to session hash
        try:
            import streamlit.runtime.caching.hashing as hashing
            return str(hash(str(st.session_state)))[:10]
        except:
            return "default_user"
    
    def is_allowed(self, request_type: str = "query") -> tuple[bool, Optional[str]]:
        """Check if request is allowed under rate limits"""
        user_id = self.get_user_id()
        current_time = time.time()
        
        with self.lock:
            user_requests = self.requests[user_id]
            
            # Clean old requests (older than 1 hour)
            while user_requests and current_time - user_requests[0] > 3600:
                user_requests.popleft()
            
            # Count requests in different time windows
            minute_count = sum(1 for req_time in user_requests if current_time - req_time < 60)
            hour_count = len(user_requests)
            
            # Check limits based on request type
            if request_type == "function_call":
                if minute_count >= self.limits["function_calls_per_minute"]:
                    return False, f"Rate limit exceeded: {self.limits['function_calls_per_minute']} function calls per minute"
                if hour_count >= self.limits["function_calls_per_hour"]:
                    return False, f"Rate limit exceeded: {self.limits['function_calls_per_hour']} function calls per hour"
            else:  # regular query
                if minute_count >= self.limits["queries_per_minute"]:
                    return False, f"Rate limit exceeded: {self.limits['queries_per_minute']} queries per minute"
                if hour_count >= self.limits["queries_per_hour"]:
                    return False, f"Rate limit exceeded: {self.limits['queries_per_hour']} queries per hour"
            
            # Add current request
            user_requests.append(current_time)
            return True, None
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        user_id = self.get_user_id()
        current_time = time.time()
        
        with self.lock:
            user_requests = self.requests[user_id]
            
            minute_count = sum(1 for req_time in user_requests if current_time - req_time < 60)
            hour_count = sum(1 for req_time in user_requests if current_time - req_time < 3600)
            
            return {
                "requests_last_minute": minute_count,
                "requests_last_hour": hour_count,
                "limits": self.limits,
                "user_id": user_id
            }

# Global rate limiter
rate_limiter = RateLimiter()

def rate_limit(request_type: str = "query"):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            allowed, message = rate_limiter.is_allowed(request_type)
            if not allowed:
                raise Exception(f"Rate limit exceeded: {message}")
            return func(*args, **kwargs)
        return wrapper
    return decorator