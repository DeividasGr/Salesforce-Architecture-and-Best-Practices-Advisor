from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import os
import hashlib
from typing import List, Dict, Any

class SalesforceDocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""],
            length_function=len,
        )
        
        # Document type mapping for better categorization
        self.doc_type_mapping = {
            "salesforce_apex_developer_guide.pdf": {
                "type": "development",
                "category": "core_programming",
                "topics": "apex,triggers,classes,governor_limits"
            },
            "salesforce_security_impl_guide.pdf": {
                "type": "security", 
                "category": "implementation",
                "topics": "authentication,authorization,data_security"
            },
            "integration_patterns_and_practices.pdf": {
                "type": "integration",
                "category": "architecture", 
                "topics": "apis,patterns,enterprise_integration"
            },
            "sfdx_dev.pdf": {
                "type": "devops",
                "category": "development_lifecycle",
                "topics": "sfdx,deployment,version_control"
            },
            "salesforce_soql_sosl.pdf": {
                "type": "data",
                "category": "querying",
                "topics": "soql,sosl,query_optimization"
            },
            "api_meta.pdf": {
                "type": "api",
                "category": "deployment",
                "topics": "metadata,deployment,automation"
            },
            "api_rest.pdf": {
                "type": "api",
                "category": "integration", 
                "topics": "rest,api_design,integration"
            },
            "salesforce_app_limits_cheatsheet.pdf": {
                "type": "performance",
                "category": "best_practices",
                "topics": "governor_limits,performance,optimization"
            },
            "platform_events.pdf": {
                "type": "development",
                "category": "core_programming",
                "topics": "apex,triggers,classes,governor_limits,performance,optimization"
            }
        }
    
    def filter_metadata_for_chromadb(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Filter metadata to only include ChromaDB-compatible types"""
        filtered = {}
        
        for key, value in metadata.items():
            # ChromaDB only accepts: str, int, float, bool, None
            if isinstance(value, (str, int, float, bool)) or value is None:
                filtered[key] = value
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                filtered[key] = ",".join(str(item) for item in value)
            elif isinstance(value, dict):
                # Convert dicts to JSON strings
                import json
                filtered[key] = json.dumps(value)
            else:
                # Convert other types to strings
                filtered[key] = str(value)
        
        return filtered
    
    def load_pdf(self, pdf_path: str) -> List[Document]:
        """Load and split a single PDF with ChromaDB-compatible metadata"""
        print(f"Loading PDF: {pdf_path}")
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        
        filename = os.path.basename(pdf_path)
        doc_info = self.doc_type_mapping.get(filename, {
            "type": "general",
            "category": "unknown", 
            "topics": "general"
        })
        
        # Process each document
        processed_docs = []
        for i, doc in enumerate(documents):
            # Create clean metadata (only simple types)
            clean_metadata = {
                "source_file": filename,
                "document_type": doc_info["type"],
                "category": doc_info["category"],
                "topics": doc_info["topics"],
                "page_number": i + 1,
                "chunk_id": self._generate_chunk_id(filename, i),
                "doc_size": len(doc.page_content)
            }
            
            # Filter metadata to ensure compatibility
            doc.metadata = self.filter_metadata_for_chromadb(clean_metadata)
            processed_docs.append(doc)
        
        # Split documents into chunks
        chunks = self.text_splitter.split_documents(processed_docs)
        
        # Add chunk-specific metadata
        final_chunks = []
        for i, chunk in enumerate(chunks):
            # Add chunk metadata
            chunk_metadata = chunk.metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "chunk_size": len(chunk.page_content)
            })
            
            # Filter again to be safe
            chunk.metadata = self.filter_metadata_for_chromadb(chunk_metadata)
            final_chunks.append(chunk)
        
        print(f"Created {len(final_chunks)} chunks from {filename}")
        return final_chunks
    
    def process_all_pdfs(self, pdf_directory: str) -> List[Document]:
        """Process all PDFs in directory"""
        all_chunks = []
        
        for filename in sorted(os.listdir(pdf_directory)):
            if filename.endswith('.pdf'):
                pdf_path = os.path.join(pdf_directory, filename)
                try:
                    chunks = self.load_pdf(pdf_path)
                    all_chunks.extend(chunks)
                except Exception as e:
                    print(f"❌ Error processing {filename}: {e}")
                    continue
        
        print(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
    
    def _generate_chunk_id(self, filename: str, page_num: int) -> str:
        """Generate unique chunk ID"""
        content = f"{filename}_{page_num}"
        return hashlib.md5(content.encode()).hexdigest()[:8]