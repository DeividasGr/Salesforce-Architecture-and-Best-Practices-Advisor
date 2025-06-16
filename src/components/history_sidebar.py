import streamlit as st
from datetime import datetime
from src.conversation_history import conversation_history

def render_history_sidebar():
    """Render conversation history in sidebar - simple version"""
    with st.sidebar:
        st.header("💬 Chat History")
        
        # Clear history button
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                if st.session_state.get("confirm_clear", False):
                    conversation_history.clear_history()
                    st.session_state.confirm_clear = False
                    st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("Click again to confirm")
        
        with col2:
            # Show conversation stats
            summary = conversation_history.get_conversation_summary()
            if summary["total_messages"] > 0:
                st.metric("Q&As", summary["user_messages"])
        
        # Display recent messages (last 5 Q&A pairs)
        messages = conversation_history.get_messages()
        if messages:
            st.subheader("Recent Questions")
            
            # Group messages into Q&A pairs
            qa_pairs = []
            current_user_msg = None
            
            for msg in messages:
                if msg["role"] == "user":
                    current_user_msg = msg
                elif msg["role"] == "assistant" and current_user_msg:
                    qa_pairs.append((current_user_msg, msg))
                    current_user_msg = None
            
            # Show last 5 Q&A pairs
            for i, (user_msg, assistant_msg) in enumerate(reversed(qa_pairs[-5:])):
                # Format timestamp
                time_str = datetime.fromisoformat(user_msg["timestamp"]).strftime("%H:%M")
                
                # Truncate question for display
                question = user_msg["content"]
                if len(question) > 50:
                    question = question[:50] + "..."
                
                # Display as expandable section
                with st.expander(f"🕐 {time_str} • {question}", expanded=False):
                    st.write(f"**Q:** {user_msg['content']}")
                    
                    # Show tool used if available
                    if assistant_msg["metadata"].get("tool_used"):
                        st.caption(f"🔧 {assistant_msg['metadata']['tool_used']}")
                    
                    # Show first 200 chars of answer
                    answer_preview = assistant_msg["content"][:200] + "..." if len(assistant_msg["content"]) > 200 else assistant_msg["content"]
                    st.write(f"**A:** {answer_preview}")
                    
        else:
            st.info("Start chatting to see your conversation history here!")