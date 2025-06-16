import streamlit as st
import json
import csv
import io
from datetime import datetime
from src.conversation_history import conversation_history

def export_to_json() -> str:
    """Export conversation to JSON format"""
    messages = conversation_history.get_messages()
    summary = conversation_history.get_conversation_summary()
    
    export_data = {
        "export_info": {
            "export_date": datetime.now().isoformat(),
            "app_name": "Salesforce RAG Advisor",
            "format": "json"
        },
        "conversation_summary": summary,
        "messages": messages
    }
    
    return json.dumps(export_data, indent=2)

def export_to_csv() -> str:
    """Export conversation to CSV format"""
    messages = conversation_history.get_messages()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["timestamp", "role", "content", "tool_used", "sources_count"])
    
    # Write messages
    for msg in messages:
        writer.writerow([
            msg["timestamp"],
            msg["role"],
            msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"],  # Truncate long content
            msg["metadata"].get("tool_used", ""),
            msg["metadata"].get("sources_count", "")
        ])
    
    return output.getvalue()

def export_to_markdown() -> str:
    """Export conversation to Markdown format"""
    messages = conversation_history.get_messages()
    summary = conversation_history.get_conversation_summary()
    
    # Create markdown content
    content = f"""# Salesforce RAG Conversation Export

**Export Date:** {datetime.now().strftime('%B %d, %Y at %H:%M')}
**Total Messages:** {summary['total_messages']}
**Questions Asked:** {summary['user_messages']}

---

"""
    
    current_pair = 1
    user_msg = None
    
    for msg in messages:
        if msg["role"] == "user":
            user_msg = msg
        elif msg["role"] == "assistant" and user_msg:
            # Write Q&A pair
            content += f"## Q{current_pair}: {user_msg['content']}\n\n"
            content += f"**Asked:** {user_msg['timestamp']}\n\n"
            
            content += f"**Answer:**\n{msg['content']}\n\n"
            
            # Add metadata if available
            if msg["metadata"].get("tool_used"):
                content += f"**Tool Used:** {msg['metadata']['tool_used']}\n\n"
            
            if msg["metadata"].get("sources_count"):
                content += f"**Sources:** {msg['metadata']['sources_count']} documents\n\n"
            
            content += "---\n\n"
            current_pair += 1
            user_msg = None
    
    return content

def render_export_section():
    """Render simple export section in sidebar with direct downloads"""
    with st.sidebar:
        st.header("📥 Export Chat")
        
        messages = conversation_history.get_messages()
        if not messages:
            st.info("No conversation to export yet.")
            return
        
        summary = conversation_history.get_conversation_summary()
        st.write(f"**{summary['user_messages']} questions** • **{summary['total_messages']} total messages**")
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Direct download buttons without additional steps
        col1, col2, col3 = st.columns(3)
        
        with col1:
            json_data = export_to_json()
            st.download_button(
                "📄 JSON",
                json_data,
                f"salesforce_chat_{timestamp}.json",
                "application/json",
                help="Download as JSON file",
                use_container_width=True
            )
        
        with col2:
            csv_data = export_to_csv()
            st.download_button(
                "📊 CSV",
                csv_data,
                f"salesforce_chat_{timestamp}.csv",
                "text/csv",
                help="Download as CSV file",
                use_container_width=True
            )
        
        with col3:
            md_data = export_to_markdown()
            st.download_button(
                "📝 MD",
                md_data,
                f"salesforce_chat_{timestamp}.md",
                "text/markdown",
                help="Download as Markdown file",
                use_container_width=True
            )