import streamlit as st
from datetime import datetime
from typing import List, Dict, Any

class SimpleConversationHistory:
    """Simple conversation history using only session state"""
    
    def __init__(self):
        # Initialize session state for messages if not exists
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to the conversation history"""
        message = {
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        st.session_state.messages.append(message)
        
    def get_messages(self) -> List[Dict]:
        """Get all messages"""
        return st.session_state.messages
    
    def clear_history(self):
        """Clear conversation history"""
        st.session_state.messages = []
        
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get simple conversation statistics"""
        messages = self.get_messages()
        user_messages = [m for m in messages if m["role"] == "user"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        
        return {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "start_time": messages[0]["timestamp"] if messages else None,
            "last_time": messages[-1]["timestamp"] if messages else None
        }

conversation_history = SimpleConversationHistory()
    