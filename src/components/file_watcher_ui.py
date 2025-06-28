# src/components/file_watcher_ui.py - Simplified upload UI components
import streamlit as st


def render_file_upload_section():
    """Render simplified file upload section with direct processing"""
    st.header("📁 Add Documents")
    
    # Initialize session state for processed files
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
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            st.error("❌ File too large. Please upload PDFs smaller than 50MB.")
            return
        
        # Check if this file has already been processed
        file_key = f"{uploaded_file.name}_{file_size}"
        already_processed = file_key in st.session_state.processed_files
        
        if already_processed:
            # Show file info and success message only
            st.caption(f"📄 File: {uploaded_file.name} ({file_size / 1024 / 1024:.1f} MB)")
            st.success("✅ Document successfully added to knowledge base")
        else:
            # Show process button for new files
            st.caption(f"📄 File: {uploaded_file.name} ({file_size / 1024 / 1024:.1f} MB)")
            
            if st.button("🚀 Process & Add to Knowledge Base", type="primary"):
                try:
                    # Save uploaded file to data/raw directory
                    import os
                    pdf_directory = "data/raw"
                    os.makedirs(pdf_directory, exist_ok=True)
                    
                    file_path = os.path.join(pdf_directory, uploaded_file.name)
                    
                    # Check if file already exists
                    if os.path.exists(file_path):
                        st.warning(f"⚠️ File '{uploaded_file.name}' already exists. Overwriting...")
                    
                    # Write the uploaded file
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process immediately using RAG system
                    rag_system = st.session_state.get('rag_system')
                    if rag_system:
                        with st.spinner(f"📄 Processing {uploaded_file.name}..."):
                            # Process PDF directly
                            documents = rag_system.process_single_pdf(file_path)
                            
                            if documents:
                                # Add to vector store immediately (with metadata update for proper retrieval)
                                rag_system.add_documents_to_vectorstore(documents, file_path, update_metadata=True)
                                
                                # Mark as processed
                                st.session_state.processed_files.add(file_key)
                                
                                # Show simple success message
                                st.success("✅ Document successfully added to knowledge base")
                                st.rerun()  # Refresh to hide the button
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
        
        # Upload section (main feature)
        render_file_upload_section()

