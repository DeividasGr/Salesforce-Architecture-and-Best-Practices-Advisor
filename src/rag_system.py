# src/rag_system.py - Persistent storage with smart loading
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.documents import Document
import chromadb
import os
from dotenv import load_dotenv
import json
import hashlib
import time
import html
from typing import List, Dict, Any
from src.monitoring import monitor, track_query
from src.rate_limiter import rate_limit
from src.input_validator import validator
from src.salesforce_tools import governor_limits_calculator, soql_query_optimizer, apex_code_reviewer
from src.token_tracker import token_tracker

load_dotenv()

class SalesforceRAGSystem:
    def __init__(self, persist_directory: str = "data/vectorstore_persistent"):
        self.persist_directory = persist_directory
        
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_api_key,
            task_type="RETRIEVAL_DOCUMENT"
        )
        self.vectorstore = None
        self.qa_chain = None
        self.collection_name = "salesforce_docs"
        self.metadata_file = os.path.join(persist_directory, "metadata.json")
    
    def _get_pdf_fingerprint(self, pdf_directory: str) -> str:
        """Create a fingerprint of all PDFs to detect changes"""
        pdf_info = {}
        
        if not os.path.exists(pdf_directory):
            return ""
        
        for filename in sorted(os.listdir(pdf_directory)):
            if filename.endswith('.pdf'):
                filepath = os.path.join(pdf_directory, filename)
                try:
                    stat = os.stat(filepath)
                    pdf_info[filename] = {
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    }
                except OSError:
                    continue
        
        info_str = json.dumps(pdf_info, sort_keys=True)
        return hashlib.md5(info_str.encode()).hexdigest()
    
    def _save_metadata(self, pdf_fingerprint: str, document_count: int):
        """Save metadata about the vector store"""
        os.makedirs(self.persist_directory, exist_ok=True)
        metadata = {
            'pdf_fingerprint': pdf_fingerprint,
            'document_count': document_count,
            'created_at': time.time()
        }
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f)
    
    def _load_metadata(self) -> Dict:
        """Load metadata about the vector store"""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def needs_rebuild(self, pdf_directory: str) -> bool:
        """Check if vector store needs to be rebuilt"""
        if not os.path.exists(self.persist_directory):
            print("📁 No vector store directory found")
            return True
        
        try:
            client = chromadb.PersistentClient(path=self.persist_directory)
            collections = client.list_collections()
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                print("📊 Collection not found")
                return True
            
            collection = client.get_collection(self.collection_name)
            if collection.count() == 0:
                print("📋 Collection is empty")
                return True
            
        except Exception as e:
            print(f"❌ Error checking collection: {e}")
            return True
        
        current_fingerprint = self._get_pdf_fingerprint(pdf_directory)
        stored_metadata = self._load_metadata()
        stored_fingerprint = stored_metadata.get('pdf_fingerprint', '')
        
        if current_fingerprint != stored_fingerprint:
            print("📄 PDFs have changed since last build")
            return True
        
        print("✅ Vector store is up to date")
        return False
    
    def create_vectorstore(self, documents: List[Document], pdf_directory: str):
        """Create ChromaDB vector store with persistence"""
        print(f"Creating persistent ChromaDB vector store with {len(documents)} chunks...")
        
        # Stop any existing file watcher to release locks (only for initial creation)
        try:
            from src.file_watcher_v2 import stop_file_watcher
            stop_file_watcher()
        except:
            pass  # May not exist yet
        
        if os.path.exists(self.persist_directory):
            import shutil
            try:
                # Wait longer and try multiple times
                for attempt in range(3):
                    try:
                        shutil.rmtree(self.persist_directory)
                        time.sleep(2)
                        print("🗑️ Removed existing vector store")
                        break
                    except Exception as e:
                        if attempt < 2:
                            print(f"⚠️ Attempt {attempt + 1} failed, retrying...")
                            time.sleep(3)
                        else:
                            print(f"⚠️ Could not remove existing vector store: {e}")
                            timestamp = int(time.time())
                            self.persist_directory = f"{self.persist_directory}_{timestamp}"
                            self.metadata_file = os.path.join(self.persist_directory, "metadata.json")
            except Exception as e:
                print(f"⚠️ Could not remove existing vector store: {e}")
                timestamp = int(time.time())
                self.persist_directory = f"{self.persist_directory}_{timestamp}"
                self.metadata_file = os.path.join(self.persist_directory, "metadata.json")
        
        try:
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
                collection_name=self.collection_name,
                collection_metadata={"description": "Salesforce Architecture & Best Practices Knowledge Base"}
            )
            
            print(f"✅ Vector store created and persisted to {self.persist_directory}")
            
            pdf_fingerprint = self._get_pdf_fingerprint(pdf_directory)
            self._save_metadata(pdf_fingerprint, len(documents))
            
            count = len(self.vectorstore.get()['ids'])
            print(f"Successfully created vector store with {count} documents")
            
        except Exception as e:
            print(f"❌ Error creating vectorstore: {e}")
            raise
    
    def load_vectorstore(self):
        """Load existing persistent vector store"""
        print("📂 Loading existing vector store...")
        
        try:
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            
            count = len(self.vectorstore.get()['ids'])
            print(f"✅ Loaded vector store with {count} documents")
            
        except Exception as e:
            print(f"❌ Error loading vectorstore: {e}")
            raise
    
    def setup_qa_chain(self):
        """Setup simple function calling approach"""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        
        # Create LLM (token tracking added per call)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
            max_output_tokens=2048
        )
        
        # Create retriever
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        
        print("✅ Simple function calling setup complete")

    @track_query
    @rate_limit("query")
    def query(self, question: str) -> Dict[str, Any]:
        """Query with manual function calling detection"""
        
        is_valid, message, cleaned_question = validator.validate_question(question)
        if not is_valid:
            monitor.log_system_event("validation_failed", {"question": question[:50], "reason": message})
            raise ValueError(f"Input validation failed: {message}")
        
        # Use cleaned question
        question = cleaned_question
        
        if not hasattr(self, 'llm') or not self.llm:
            self.setup_qa_chain()
        
        print(f"Processing query: {question}")
        monitor.log_system_event("query_started", {"question": question[:50]})
        
        # Check if question needs function calling
        question_lower = question.lower()
        function_result = None
        tool_used = None
        
        # 1. GOVERNOR LIMITS CALCULATION DETECTION - require JSON data
        if (any(keyword in question_lower for keyword in ["governor", "limits", "calculate", "usage"]) and 
            "{" in question and "}" in question):
            
            # Extract JSON part and decode HTML entities
            json_start = question.find("{")
            json_end = question.rfind("}") + 1
            operations = question[json_start:json_end] if json_start >= 0 and json_end > json_start else question
            
            # Decode HTML entities (need to decode twice for double-encoded content)
            operations = html.unescape(operations)
            operations = html.unescape(operations)
            
            function_result = governor_limits_calculator.invoke({"operations": operations})
            tool_used = "📊 Governor Limits Calculator"
        
        # 2. APEX CODE REVIEW DETECTION - require strong code indicators
        elif (any(strong_code in question for strong_code in ["public class", "public static", "private class", "private static"]) or
              ("{" in question and any(code_word in question for code_word in ["public", "private", "void", "return", "if(", "for(", "while("])) or
              ("trigger " in question.lower() and "{" in question)):
            # Look for actual code in the question  
            if True:  # We already checked for strong indicators above
                # Extract code (look for code patterns)
                code_start = -1
                for pattern in ["public class", "trigger", "public", "private"]:
                    if pattern in question:
                        code_start = question.find(pattern)
                        break
                
                if code_start >= 0:
                    code = question[code_start:]
                else:
                    # Look for code-like patterns
                    if "{" in question and "}" in question:
                        brace_start = question.find("{")
                        code = question[:brace_start + question[brace_start:].find("}") + 1]
                    else:
                        code = question
                
                print(f"📝 Extracted code: {code[:100]}...")
                function_result = apex_code_reviewer.invoke({"code": code})
                tool_used = "🔧 Apex Code Reviewer"
        
        # 3. SOQL QUERY OPTIMIZATION DETECTION - require actual SELECT statement
        elif "select" in question_lower and "from" in question_lower:
            if "select" in question_lower:
                # Find and extract SELECT statement
                select_start = question_lower.find("select")
                query_part = question[select_start:] if select_start >= 0 else question
                
                # Clean up the query - look for SQL keywords to determine end
                lines = query_part.split('\n')
                clean_query_parts = []
                
                for line in lines:
                    line = line.strip()
                    if line and any(sql_word in line.lower() for sql_word in ['select', 'from', 'where', 'order', 'limit', 'group', 'having']):
                        clean_query_parts.append(line)
                    elif clean_query_parts and not any(char in line for char in ['?', ':', 'can', 'you', 'please', 'optimize']):
                        # Continue if it looks like part of the query
                        clean_query_parts.append(line)
                
                final_query = ' '.join(clean_query_parts) if clean_query_parts else query_part.strip()
                
                # Remove common question words from the end
                for word in [' ?', '?', ' optimize', ' query']:
                    if final_query.lower().endswith(word):
                        final_query = final_query[:-len(word)].strip()
                
                print(f"📝 Extracted query: {final_query}")
                function_result = soql_query_optimizer.invoke({"query": final_query})
                tool_used = "⚡ SOQL Query Optimizer"
        
        # 4. RETURN FUNCTION CALLING RESULT
        if function_result and tool_used:
            print(f"✅ Function calling successful with {tool_used}")
            
            # Get some context from documents for additional info
            docs = self.retriever.invoke(question)
            
            # Combine function result with relevant documentation
            enhanced_answer = f"## {tool_used} Results:\n\n{function_result}"
            
            if docs:
                enhanced_answer += f"\n\n---\n\n## 📚 Related Salesforce Documentation:\n\n"
                for i, doc in enumerate(docs[:2]):  # Show top 2 relevant docs
                    doc_context = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                    enhanced_answer += f"**{i+1}. From {doc.metadata.get('source_file', 'Salesforce Docs')}:**\n{doc_context}\n\n"
            
            # Manual token tracking for function calling (no LLM tokens used)
            token_tracker._update_session_stats({
                'input_tokens': 0,  # Function calling uses no LLM tokens
                'output_tokens': 0,
                'total_tokens': 0,
                'model': 'function-call',
                'response_time': 0.1,  # Minimal processing time
                'timestamp': __import__('datetime').datetime.now().isoformat(),
                'cost': 0.0,  # No cost for function calling
                'estimated': False
            })
            
            return {
                "answer": enhanced_answer,
                "sources": docs[:3] if docs else [],
                "source_metadata": [doc.metadata for doc in docs[:3]] if docs else [],
                "tool_used": tool_used
            }
        
        # 5. REGULAR RAG FOR NON-FUNCTION QUESTIONS
        print("📚 Using regular RAG (no function calling detected)")
        docs = self.retriever.invoke(question)
        
        if not docs:
            return {
                "answer": "I couldn't find relevant information in the Salesforce documentation for your question. Please try rephrasing or asking about specific Salesforce topics like Apex, SOQL, governor limits, security, or integration patterns.",
                "sources": [],
                "source_metadata": []
            }
        
        # Create context from documents
        context = ""
        for i, doc in enumerate(docs[:3]):
            source_file = doc.metadata.get('source_file', 'Unknown')
            content = doc.page_content[:800] + "..." if len(doc.page_content) > 800 else doc.page_content
            context += f"\n\n--- Source {i+1}: {source_file} ---\n{content}"
        
        # Create prompt for regular RAG
        prompt_text = f"""You are a Salesforce Architecture & Best Practices Advisor. Use the following context from official Salesforce documentation to provide expert guidance.

Context from Salesforce Documentation:{context}

Question: {question}

Instructions:
- Provide detailed, actionable advice based on the Salesforce documentation
- Include specific examples and code snippets when relevant
- Reference best practices and governor limits when applicable
- Mention security considerations when relevant
- Cite which Salesforce guide the information comes from
- If the question involves architecture decisions, provide pros/cons of different approaches

Provide a comprehensive answer:"""
        
        # Get response from LLM with token tracking
        try:
            response = self.llm.invoke(prompt_text, config={"callbacks": [token_tracker]})
            answer = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            print(f"❌ Error getting LLM response: {e}")
            answer = "I encountered an error processing your question. Please try again or rephrase your question."
        
        return {
            "answer": answer,
            "sources": docs,
            "source_metadata": [doc.metadata for doc in docs]
        }
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Direct similarity search for debugging"""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        
        return self.vectorstore.similarity_search(query, k=k)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information"""
        if not self.vectorstore:
            return {"error": "Vector store not initialized"}
        
        try:
            collection_data = self.vectorstore.get()
            metadata = self._load_metadata()
            
            return {
                "name": self.collection_name,
                "count": len(collection_data['ids']),
                "directory": self.persist_directory,
                "created_at": metadata.get('created_at'),
                "pdf_fingerprint": metadata.get('pdf_fingerprint', 'unknown')[:8]
            }
        except Exception as e:
            return {"error": f"Failed to get collection info: {str(e)}"}
    
    def process_single_pdf(self, pdf_path: str) -> List[Document]:
        """Process a single PDF file and return documents"""
        from src.document_processor import SalesforceDocumentProcessor
        
        print(f"📄 Processing single PDF: {os.path.basename(pdf_path)}")
        processor = SalesforceDocumentProcessor()
        
        # Process just this PDF
        documents = processor.load_pdf(pdf_path)
        print(f"📝 Generated {len(documents)} chunks from {os.path.basename(pdf_path)}")
        
        return documents
    
    def add_documents_to_vectorstore(self, documents: List[Document], pdf_path: str, update_metadata: bool = True):
        """Add new documents to existing vector store with optimizations"""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        
        filename = os.path.basename(pdf_path)
        print(f"➕ Adding {len(documents)} documents from {filename}...")
        
        try:
            # Batch add documents for better performance
            if documents:
                # Add all documents in one batch operation
                self.vectorstore.add_documents(documents)
                
                # Skip metadata update for faster uploads (optional)
                if update_metadata:
                    self._update_metadata_after_change(pdf_path)
                
                # Get final count for reporting (lightweight operation)
                current_count = len(self.vectorstore.get()['ids'])
                print(f"✅ Added {len(documents)} documents from {filename}. Total: {current_count}")
            else:
                print(f"⚠️ No documents to add from {filename}")
            
        except Exception as e:
            print(f"❌ Error adding documents from {filename}: {e}")
            raise
    
    def remove_documents_by_source(self, pdf_path: str):
        """Remove documents from a specific PDF file using ChromaDB best practices"""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        
        filename = os.path.basename(pdf_path)
        print(f"🗑️ Removing documents from {filename}...")
        
        try:
            # Use ChromaDB's where clause for efficient deletion
            # This is much faster than getting all documents and filtering
            delete_result = self.vectorstore.delete(where={"source_file": filename})
            
            # Check how many were deleted
            if hasattr(delete_result, '__len__'):
                deleted_count = len(delete_result) if delete_result else 0
            else:
                # Fallback: check collection count before/after
                deleted_count = "unknown"
            
            print(f"🗑️ Removed {deleted_count} documents from {filename}")
            
            # Update metadata after deletion
            self._update_metadata_after_change(pdf_path)
                
        except Exception as e:
            print(f"❌ Error removing documents from {filename}: {e}")
            # Don't raise - continue processing
    
    def _update_metadata_after_change(self, pdf_path: str):
        """Update metadata after vector store changes"""
        try:
            pdf_directory = os.path.dirname(pdf_path)
            new_fingerprint = self._get_pdf_fingerprint(pdf_directory)
            current_count = len(self.vectorstore.get()['ids'])
            self._save_metadata(new_fingerprint, current_count)
        except Exception as e:
            print(f"⚠️ Warning: Could not update metadata: {e}")
    
    def handle_file_change(self, file_path: str, event_type: str):
        """Handle real-time file changes with duplicate prevention"""
        filename = os.path.basename(file_path)
        print(f"🔄 Processing file change: {event_type} - {filename}")
        
        # Skip processing if file doesn't exist or isn't a PDF
        if not os.path.exists(file_path) or not file_path.lower().endswith('.pdf'):
            print(f"⚠️ Skipping non-PDF or missing file: {filename}")
            return
        
        # Check if we're already processing this file
        processing_key = f"processing_{filename}"
        if hasattr(self, processing_key) and getattr(self, processing_key, False):
            print(f"⏳ Already processing {filename}, skipping duplicate...")
            return
        
        try:
            # Mark as processing
            setattr(self, processing_key, True)
            
            if event_type == "created" or event_type == "modified":
                # For modifications, remove existing documents first
                if event_type == "modified":
                    print(f"🗑️ Removing existing documents for modified file: {filename}")
                    self.remove_documents_by_source(file_path)
                
                # Process and add new documents
                print(f"📄 Processing {filename}...")
                documents = self.process_single_pdf(file_path)
                if documents:
                    print(f"➕ Adding {len(documents)} documents from {filename}")
                    self.add_documents_to_vectorstore(documents, file_path)
                    monitor.log_system_event("pdf_processed", {
                        "filename": filename,
                        "event_type": event_type,
                        "document_count": len(documents)
                    })
                else:
                    print(f"⚠️ No documents generated from {filename}")
                    
            elif event_type == "deleted":
                # Remove documents from deleted PDF
                print(f"🗑️ Removing documents for deleted file: {filename}")
                self.remove_documents_by_source(file_path)
                monitor.log_system_event("pdf_removed", {
                    "filename": filename
                })
            
            print(f"✅ Successfully processed {event_type} event for {filename}")
            
        except Exception as e:
            print(f"❌ Error handling file change for {filename}: {e}")
            monitor.log_system_event("file_change_error", {
                "filename": filename,
                "event_type": event_type,
                "error": str(e)
            })
            # Don't re-raise to prevent breaking the watcher
        finally:
            # Mark as not processing
            setattr(self, processing_key, False)