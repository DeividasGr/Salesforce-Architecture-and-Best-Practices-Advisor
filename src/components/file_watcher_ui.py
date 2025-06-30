import streamlit as st
import time
import os


def render_file_upload_section():
    """Render simplified file upload section with direct processing"""
    st.header("📁 Add Documents")
    
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()
    
    uploaded_file = st.file_uploader(
        "Upload PDF to Knowledge Base",
        type="pdf",
        help="Upload Salesforce documentation to expand the knowledge base",
        key="pdf_uploader_simple"
    )
    
    if uploaded_file is not None:
        # Check file size (limit to 50MB for reasonable processing time)
        file_size = len(uploaded_file.getbuffer())
        if file_size > 50 * 1024 * 1024:
            st.error("❌ File too large. Please upload PDFs smaller than 50MB.")
            return
        
        # Check if this file has already been processed
        file_key = f"{uploaded_file.name}_{file_size}"
        already_processed = file_key in st.session_state.processed_files
        
        if already_processed:
            # Show file info and success message only
            st.caption(f"📄 File: {uploaded_file.name} ({file_size / 1024 / 1024:.1f} MB)")
            success_msg = st.success("✅ Document successfully added to knowledge base")
            time.sleep(3)
            success_msg.empty()
        else:
            # Show process button for new files
            st.caption(f"📄 File: {uploaded_file.name} ({file_size / 1024 / 1024:.1f} MB)")
            
            if st.button("🚀 Process & Add to Knowledge Base", type="primary"):
                try:
                    pdf_directory = "data/raw"
                    os.makedirs(pdf_directory, exist_ok=True)
                    
                    file_path = os.path.join(pdf_directory, uploaded_file.name)
                    
                    if os.path.exists(file_path):
                        st.warning(f"⚠️ File '{uploaded_file.name}' already exists. Overwriting...")
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process immediately using RAG system
                    rag_system = st.session_state.get('rag_system')
                    if rag_system:
                        with st.spinner(f"📄 Processing {uploaded_file.name}..."):

                            documents = rag_system.process_single_pdf(file_path)
                            
                            if documents:
                                # Add to vector store immediately (with metadata update for proper retrieval)
                                rag_system.add_documents_to_vectorstore(documents, file_path, update_metadata=True)
                                
                                st.session_state.processed_files.add(file_key)
  
                                success_msg = st.success("✅ Document successfully added to knowledge base")
                                time.sleep(3)
                                success_msg.empty()
                                
                                st.rerun()
                            else:
                                st.error(f"❌ No content could be extracted from {uploaded_file.name}")
                    else:
                        st.error("❌ RAG system not initialized. Please refresh the page.")
                        
                except Exception as e:
                    st.error(f"❌ Error processing file: {str(e)}")


def render_file_watcher_sidebar():
    """Simplified upload sidebar component"""
    with st.sidebar:
        st.divider()
        
        render_file_upload_section()

