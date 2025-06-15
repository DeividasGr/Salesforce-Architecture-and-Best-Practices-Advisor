# app.py - Fixed variable scope
import streamlit as st
import os
from dotenv import load_dotenv
from src.document_processor import SalesforceDocumentProcessor
from src.rag_system import SalesforceRAGSystem

# Load environment variables
load_dotenv()

# Page config
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

def initialize_rag_system():
    """Initialize RAG system with smart loading"""
    pdf_directory = "data/raw"
    rag_system = SalesforceRAGSystem()
    
    # Check for PDFs first
    if not os.path.exists(pdf_directory):
        st.error("❌ PDF directory 'data/raw' not found!")
        st.stop()
    
    pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith('.pdf')]
    if not pdf_files:
        st.error("❌ No PDF files found in 'data/raw' directory!")
        st.stop()
    
    # Check if we need to rebuild
    if not rag_system.needs_rebuild(pdf_directory):
        try:
            with st.spinner("📂 Loading existing knowledge base..."):
                rag_system.load_vectorstore()
                info = rag_system.get_collection_info()
                st.success(f"✅ Loaded existing knowledge base with {info['count']} documents")
                rag_system.setup_qa_chain()
                return rag_system
        except Exception as e:
            st.warning(f"⚠️ Failed to load existing vector store: {str(e)}")
            st.info("🔄 Creating new vector store...")
    
    # Create new vector store
    st.info("📚 Building knowledge base from PDFs...")
    
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

def main():
    st.title("⚡ Salesforce Architecture & Best Practices Advisor")
    st.markdown("Get expert guidance on Salesforce development, architecture, and best practices from official documentation.")
    st.markdown("*Powered by Google Gemini 2.0 Flash & ChromaDB*")
    
    # Sidebar with info
    with st.sidebar:
        st.header("📋 Knowledge Base")
        
        # Check for API key
        if not os.getenv("GOOGLE_API_KEY"):
            st.error("⚠️ Please set your GOOGLE_API_KEY in .env file")
            st.stop()
        
        # Initialize RAG system
        if st.session_state.rag_system is None:
            st.session_state.rag_system = initialize_rag_system()
        
        # Show collection info
        if st.session_state.rag_system:
            info = st.session_state.rag_system.get_collection_info()
            st.metric("Documents in Knowledge Base", info.get("count", "Unknown"))
            
            st.header("📖 Documentation Sources")
            sources = [
                "Apex Developer Guide",
                "Security Implementation Guide", 
                "Integration Patterns & Practices",
                "Salesforce DX Developer Guide",
                "SOQL and SOSL Reference",
                "Metadata API Guide",
                "REST API Guide", 
                "App Limits Cheat Sheet"
            ]
            for source in sources:
                st.markdown(f"• {source}")
    
    # Main chat interface
    st.subheader("💬 Ask Your Question")
    
    # Example questions
    st.markdown("**💡 Example Questions:**")
    examples = [
        "What are the best practices for handling governor limits in Apex?",
        "How should I design a secure integration with external systems?",
        "What are the different types of SOQL queries and when should I use each?",
        "How do I implement proper error handling in Apex triggers?",
        "What are the security considerations for REST API implementations?",
    ]
    
    # Create example buttons in columns
    cols = st.columns(2)
    for i, example in enumerate(examples):
        col = cols[i % 2]
        with col:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                st.session_state.current_question = example
    
    # Function calling examples section
    st.markdown("**🔧 Try Function Calling:**")
    func_cols = st.columns(3)
    
    with func_cols[0]:
        if st.button("📝 Review Apex Code", key="apex_example", use_container_width=True):
            st.session_state.current_question = """Please review this Apex code:

public class AccountProcessor {
    public void processAccounts() {
        for(Account acc : [SELECT Id, Name FROM Account]) {
            acc.Name = acc.Name + ' - Updated';
            update acc;
        }
    }
}"""
    
    with func_cols[1]:
        if st.button("⚡ Optimize SOQL", key="soql_example", use_container_width=True):
            st.session_state.current_question = """Can you optimize this SOQL query?

SELECT Id, Name, Owner.Name, CreatedBy.Name FROM Account WHERE Name LIKE '%test%' ORDER BY CreatedDate"""
    
    with func_cols[2]:
        if st.button("📊 Check Limits", key="limits_example", use_container_width=True):
            st.session_state.current_question = """Calculate governor limits usage for these operations:

{"soql_queries": 85, "dml_statements": 140, "heap_size_mb": 5}"""
    
    # Question input
    question = st.text_input(
        "Enter your question:",
        value=st.session_state.get("current_question", ""),
        placeholder="e.g., What are the best practices for handling governor limits in Apex?"
    )
    
    # Process question when button is clicked
    if question and st.button("🔍 Get Answer", type="primary"):
        with st.spinner("Searching knowledge base..."):
            try:
                result = st.session_state.rag_system.query(question)
                
                # Display answer
                st.subheader("📝 Answer:")
                st.write(result["answer"])
                
                # Check if any tools were used (look for tool indicators in the response)
                answer_text = result["answer"].lower()
                tools_used = []
                
                if any(keyword in answer_text for keyword in ["code review", "apex", "governor limit violation", "dml operation"]):
                    tools_used.append("🔧 Apex Code Reviewer")
                if any(keyword in answer_text for keyword in ["soql", "query", "optimiz", "performance", "index"]):
                    tools_used.append("⚡ SOQL Query Optimizer") 
                if any(keyword in answer_text for keyword in ["governor limit", "calculation", "usage", "percentage"]):
                    tools_used.append("📊 Governor Limits Calculator")
                
                if tools_used:
                    st.subheader("🛠️ Tools Used:")
                    for tool in tools_used:
                        st.markdown(f"• {tool}")
                
                # Display sources
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
                
                # Add to chat history
                st.session_state.chat_history.append({
                    "question": question,
                    "answer": result["answer"],
                    "sources": len(result["sources"])
                })
                
                # Clear the current question
                if "current_question" in st.session_state:
                    del st.session_state.current_question
                    st.rerun()  # Refresh to clear the input field
                
            except Exception as e:
                st.error(f"Error processing question: {str(e)}")
                st.error("Please check the console for detailed error messages.")
    
    # Chat history
    if st.session_state.chat_history:
        st.subheader("💭 Recent Questions")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history[-5:])):
            question_num = len(st.session_state.chat_history) - i
            question_preview = chat['question'][:60] + "..." if len(chat['question']) > 60 else chat['question']
            
            with st.expander(f"Q{question_num}: {question_preview}", expanded=False):
                st.markdown("**Full Question:**")
                st.markdown(f"*{chat['question']}*")
                
                st.markdown("**Answer:**")
                st.write(chat['answer'])
                
                st.markdown(f"**Sources used:** {chat['sources']}")
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Ask Again", key=f"reask_exp_{question_num}"):
                        st.session_state.current_question = chat['question']
                        st.rerun()
                
                with col2:
                    if st.button("📋 Copy Question", key=f"copy_exp_{question_num}"):
                        st.session_state.current_question = chat['question']
                        st.success("✅ Question copied to input field!")
                        st.rerun()

if __name__ == "__main__":
    main()