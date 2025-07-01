import sys
try:
    import pysqlite3
    sys.modules['sqlite3'] = pysqlite3
except ImportError:
    pass
import streamlit as st
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from src.document_processor import SalesforceDocumentProcessor
from src.rag_system import SalesforceRAGSystem
from src.monitoring import monitor, track_query
from src.rate_limiter import rate_limiter
from src.input_validator import validator

# New imports for conversation history
from src.conversation_history import conversation_history
from src.components.history_sidebar import render_history_sidebar
from src.conversation_export import render_export_section

# Import simple RAG visualizer
from src.components.rag_visualizer import SimpleRAGVisualizer, add_visualization_to_sidebar, render_simple_rag_viz

# Import token usage components
from src.components.token_usage_display import render_token_usage_sidebar, render_detailed_token_dashboard

# Import simplified upload UI
from src.components.file_watcher_ui import render_file_watcher_sidebar

load_dotenv()

st.set_page_config(
    page_title="Salesforce Architecture & Best Practices Advisor",
    page_icon="⚡",
    layout="wide"
)

# Initialize session state
if "rag_system" not in st.session_state:
    st.session_state.rag_system = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "input_key" not in st.session_state:
    st.session_state.input_key = 0
if "dropdown_key" not in st.session_state:
    st.session_state.dropdown_key = 0

# Initialize token usage tracking
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

def initialize_rag_system():
    """Initialize RAG system with smart loading"""
    pdf_directory = "data/raw"
    rag_system = SalesforceRAGSystem()
    
    if not os.path.exists(pdf_directory):
        st.error("❌ PDF directory 'data/raw' not found!")
        st.stop()
    
    pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith('.pdf')]
    if not pdf_files:
        st.error("❌ No PDF files found in 'data/raw' directory!")
        st.stop()
    
    # Always try to load existing vector store first (production mode)
    vectorstore_dir = "data/vectorstore_persistent"
    if os.path.exists(vectorstore_dir) and os.listdir(vectorstore_dir):
        try:
            with st.spinner("📂 Loading existing knowledge base..."):
                rag_system.load_vectorstore()
                info = rag_system.get_collection_info()
            
                pdf_count = len([f for f in os.listdir(pdf_directory) if f.endswith('.pdf')])
                success_msg = st.success(f"✅ Loaded knowledge base: {pdf_count} documents, {info['count']} chunks")
                time.sleep(3)
                success_msg.empty()
                
                rag_system.setup_qa_chain()
                
                return rag_system
        except Exception as e:
            st.warning(f"⚠️ Failed to load existing vector store: {str(e)}")
            st.info("🔄 Creating new vector store (first time only)...")
    else:
        st.info("📚 Creating initial knowledge base from PDFs (first time only)...")
    
    try:
        with st.spinner(f"📄 Processing {len(pdf_files)} PDF files..."):
            processor = SalesforceDocumentProcessor()
            documents = processor.process_all_pdfs(pdf_directory)
            
            if not documents:
                st.error("❌ No documents were processed from PDFs!")
                st.stop()
        
        with st.spinner("💾 Creating persistent vector database..."):
            rag_system.create_vectorstore(documents, pdf_directory)
            info = rag_system.get_collection_info()
            st.success(f"✅ Knowledge base created with {info['count']} documents")
        
        rag_system.setup_qa_chain()
        
        return rag_system
        
    except Exception as e:
        st.error(f"❌ Failed to create vector store: {str(e)}")
        st.stop()

def clear_inputs():
    """Callback function to clear inputs when button is clicked"""
    # Save the current question value before clearing for processing
    current_input = st.session_state.get("current_question", "")
    if not current_input:
        input_widget_key = f"question_input_{st.session_state.input_key}"
        current_input = st.session_state.get(input_widget_key, "")
    
    st.session_state.submitted_question = current_input
    
    st.session_state.input_key += 1
    st.session_state.dropdown_key += 1
    if "current_question" in st.session_state:
        del st.session_state.current_question

def main():
    
    st.title("⚡ Salesforce Architecture & Best Practices Advisor")
    st.markdown("Get expert guidance on Salesforce development, architecture, and best practices from official documentation.")
    st.markdown("*Powered by Google Gemini 2.0 Flash & ChromaDB*")
    
    add_visualization_to_sidebar()
    
    if st.session_state.get('show_dashboard', False):
        render_simple_rag_viz()
        st.session_state.show_dashboard = False
        return
    
    if st.session_state.get('show_token_dashboard', False):
        render_detailed_token_dashboard()
        st.session_state.show_token_dashboard = False
        return
    
    render_history_sidebar()
    render_export_section()
    render_token_usage_sidebar()
    render_file_watcher_sidebar()
    
    with st.sidebar:
        if not os.getenv("GOOGLE_API_KEY"):
            st.error("⚠️ Please set your GOOGLE_API_KEY in .env file")
            st.stop()
        
        if st.session_state.rag_system is None:
            st.session_state.rag_system = initialize_rag_system()
        
        if st.session_state.rag_system:
            pdf_count = len([f for f in os.listdir("data/raw") if f.endswith('.pdf')])
            st.metric("Documents Loaded", pdf_count)
    
    st.subheader("💬 Ask Your Question")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💡 Example Questions:**")
        examples = [
            "Select an example question...",
            "What are the best practices for handling governor limits in Apex?",
            "How should I design a secure integration with external systems?",
            "What are the different types of SOQL queries and when should I use each?",
            "How do I implement proper error handling in Apex triggers?",
            "What are the security considerations for REST API implementations?",
        ]
        
        selected_example = st.selectbox("", examples, key=f"example_dropdown_{st.session_state.dropdown_key}", label_visibility="collapsed")
        if selected_example != "Select an example question...":
            st.session_state.current_question = selected_example
    
    with col2:
        st.markdown("**🔧 Try Function Calling:**")
        function_examples = {
            "Select a function calling example...": "",
            "📝 Review Apex Code": """Please review this Apex code:

public class AccountProcessor {
    public void processAccounts() {
        for(Account acc : [SELECT Id, Name FROM Account]) {
            acc.Name = acc.Name + ' - Updated';
            update acc;
        }
    }
}""",
            "⚡ Optimize SOQL": """Can you optimize this SOQL query?

SELECT Id, Name, Owner.Name, CreatedBy.Name FROM Account WHERE Name LIKE '%test%' ORDER BY CreatedDate""",
            "📊 Check Limits": """Calculate governor limits usage for these operations:

{"soql_queries": 85, "dml_statements": 140, "heap_size_mb": 5}"""
        }
        
        selected_function = st.selectbox("", list(function_examples.keys()), key=f"function_dropdown_{st.session_state.dropdown_key}", label_visibility="collapsed")
        if selected_function != "Select a function calling example...":
            st.session_state.current_question = function_examples[selected_function]
    
    # Check if there's a reused question from history
    default_question = st.session_state.get("reuse_question", "")
    if default_question:
        del st.session_state.reuse_question
    
    current_input = st.session_state.get("current_question", default_question)
    
    col1, col2 = st.columns([4, 1])
    with col1:
        question = st.text_input(
            "Enter your question:",
            value=current_input,
            placeholder="e.g., What are the best practices for handling governor limits in Apex?",
            key=f"question_input_{st.session_state.input_key}"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        send_button = st.button("🔍 Get Answer", type="primary", use_container_width=True, on_click=clear_inputs)
    
    submitted_question = st.session_state.get("submitted_question", "")
    if submitted_question and send_button:
        is_valid, validation_message, clean_question = validator.validate_question(submitted_question)
        if not is_valid:
            st.error(f"❌ {validation_message}")
            st.stop()
    
        try:
            allowed, rate_message = rate_limiter.is_allowed("query")
            if not allowed:
                st.error(f"🚫 {rate_message}")
                st.stop()
        except Exception as e:
            st.error(f"Rate limit error: {str(e)}")
            st.stop()
        
        with st.spinner("Searching knowledge base..."):
            try:
                # Record start time for tracking
                start_time = time.time()
                
                @track_query
                def process_question(rag_system, question):
                    return rag_system.query(question)
            
                result = process_question(st.session_state.rag_system, clean_question)
                response_time = time.time() - start_time
                
                # Get visualization setting from session state
                show_viz = st.session_state.get('show_query_viz', True)
                                
                # Add visualization tracking
                visualizer = SimpleRAGVisualizer()
                visualizer.track_query(clean_question, result, response_time)
                
                if show_viz:
                    st.markdown("---")
                    visualizer.show_current_query_viz(result)
                    st.markdown("---")
                
                # Add to conversation history
                conversation_history.add_message("user", clean_question)
                conversation_history.add_message(
                    "assistant", 
                    result["answer"],
                    metadata={
                        "tool_used": result.get("tool_used"),
                        "sources_count": len(result.get("sources", [])),
                        "response_time": round(response_time, 2)
                    }
                )
                
                st.subheader("📝 Answer:")
                st.write(result["answer"])
                
                if result.get("tool_used"):
                    st.subheader("🛠️ Tools Used:")
                    st.markdown(f"• {result['tool_used']}")
                
                st.subheader("📚 Sources & References:")
                for i, (source, metadata) in enumerate(zip(result["sources"], result["source_metadata"])):
                    with st.expander(f"📄 Source {i+1}: {metadata.get('source_file', 'Unknown')}"):
                        st.write(f"**Document Type:** {metadata.get('document_type', 'Unknown')}")
                        st.write(f"**Category:** {metadata.get('category', 'Unknown')}")
                        st.write(f"**Topics:** {metadata.get('topics', 'N/A')}")
                        st.write(f"**Page:** {metadata.get('page_number', 'N/A')}")
                        
                        excerpt = source.page_content[:500] + "..." if len(source.page_content) > 500 else source.page_content
                        st.text_area(
                            f"Content from {metadata.get('source_file', 'document')}",
                            value=excerpt, 
                            height=100, 
                            disabled=True, 
                            key=f"excerpt_{i}",
                            label_visibility="collapsed"
                        )
                
                st.session_state.chat_history.append({
                    "question": submitted_question,
                    "answer": result["answer"],
                    "sources": len(result["sources"])
                })
                
                if "submitted_question" in st.session_state:
                    del st.session_state.submitted_question
                
            except Exception as e:
                st.error(f"Error processing question: {str(e)}")
                monitor.log_system_event("query_error", {
                    "question": clean_question[:100],
                    "error": str(e),
                    "user_id": rate_limiter.get_user_id()
                })
                st.error("Please check the console for detailed error messages.")
    
    if st.session_state.chat_history and not (submitted_question and send_button):
        latest_chat = st.session_state.chat_history[-1]
        st.subheader("💬 Current Conversation")
        
        with st.chat_message("user"):
            st.write(latest_chat['question'])
        
        with st.chat_message("assistant"):
            st.write(latest_chat['answer'])
            st.caption(f"📚 Sources: {latest_chat['sources']} documents")
    
    if len(st.session_state.chat_history) > 1:
        st.subheader("💭 Previous Conversations")
        
        show_previous = st.checkbox("Show conversation history", value=False)
        
        if show_previous:
            previous_chats = st.session_state.chat_history[:-1]
            for i, chat in enumerate(reversed(previous_chats[-9:])):
                chat_index = len(previous_chats) - i
                question_preview = chat['question'][:60] + "..." if len(chat['question']) > 60 else chat['question']
                
                with st.expander(f"Q{chat_index}: {question_preview}", expanded=False):
                    st.markdown("**Question:**")
                    st.markdown(f"*{chat['question']}*")
                    
                    st.markdown("**Answer:**")
                    st.write(chat['answer'])
                    
                    st.markdown(f"**Sources used:** {chat['sources']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 Ask Again", key=f"reask_{chat_index}"):
                            st.session_state.current_question = chat['question']
                            st.rerun()
                    
                    with col2:
                        if st.button("📋 Copy Question", key=f"copy_{chat_index}"):
                            st.session_state.current_question = chat['question']
                            st.success("✅ Question copied to input field!")
                            st.rerun()

if __name__ == "__main__":
    main()
