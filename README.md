# Salesforce Architecture & Best Practices Advisor

A specialized RAG (Retrieval-Augmented Generation) chatbot built with Streamlit and LangChain that provides expert guidance on Salesforce development, architecture, and best practices using official documentation.

🌐 **Live Demo**: [sfadvisor.streamlit.app](https://sfadvisor.streamlit.app)

## 🚀 Features

### 🤖 AI-Powered Code Analysis
- **Intelligent Apex Code Review**: Advanced static analysis with governor limits detection, security vulnerability scanning, and best practices enforcement
- **SOQL Query Optimization**: Performance analysis with index usage recommendations, query rewriting suggestions, and SOSL alternatives
- **Governor Limits Calculator**: Real-time usage tracking with percentage calculations, critical threshold alerts, and optimization strategies

### 📚 Knowledge Base & RAG
- **Advanced RAG Implementation**: Persistent ChromaDB vector store with Google Gemini embeddings for lightning-fast document retrieval
- **Comprehensive Documentation**: Pre-loaded with 11 official Salesforce guides including Apex Developer Guide, Security Implementation Guide, and Integration Patterns
- **Smart Document Processing**: Intelligent chunking with metadata extraction, topic categorization, and source attribution
- **Semantic Search**: Context-aware retrieval using Google's latest text-embedding-004 model

### 💬 Interactive Experience
- **Conversation Management**: Full conversation history with search, export, and reuse capabilities
- **Real-time Visualization**: Interactive RAG dashboards showing query analysis, source utilization, and response metrics
- **Multi-format Export**: Export conversations to JSON, CSV, Markdown, and PDF formats
- **Example Gallery**: Pre-built examples for common Salesforce development scenarios

## 🛠️ Technical Architecture

### Core Technologies
- **Frontend Framework**: Streamlit with custom components and interactive widgets
- **Large Language Model**: Google Gemini 2.0 Flash with function calling capabilities
- **Vector Database**: ChromaDB with persistent storage and collection management
- **Embeddings**: Google Generative AI text-embedding-004 for semantic search
- **RAG Framework**: LangChain with custom chains and document processing
- **Monitoring**: LangSmith integration for tracing and analytics

### Advanced Components
- **Document Processing**: PyPDF2 and pypdf for PDF text extraction with metadata preservation
- **Token Tracking**: Custom implementation with cost calculations and usage analytics
- **Rate Limiting**: Session-based throttling with configurable limits and grace periods
- **Visualization**: Plotly for interactive charts and RAG performance dashboards
- **Export Engine**: Multi-format export with ReportLab for PDF generation
- **Caching Strategy**: Smart vectorstore loading with fingerprint-based change detection

## 📚 Pre-loaded Knowledge Base

The application comes with a comprehensive collection of official Salesforce documentation:

### 📖 Documentation Library
- **Apex Developer Guide** (800+ pages) - Complete guide to Apex programming language
- **Security Implementation Guide** (300+ pages) - Security best practices and implementation patterns
- **Integration Patterns & Practices** (200+ pages) - Enterprise integration strategies and patterns
- **Salesforce DX Developer Guide** (400+ pages) - Modern development lifecycle and tools
- **SOQL and SOSL Reference** (150+ pages) - Complete query language documentation
- **Metadata API Developer Guide** (500+ pages) - Programmatic customization and deployment
- **REST API Developer Guide** (600+ pages) - RESTful web services and integration
- **App Limits Cheat Sheet** (50+ pages) - Governor limits and performance considerations
- **Platform Events Guide** (100+ pages) - Event-driven architecture and real-time integrations
- **Communities Developer Guide** (300+ pages) - Custom community development
- **Useful Formula Fields** (100+ pages) - Advanced formula patterns and examples

### 🔍 Search Capabilities
- **Semantic Search**: Find relevant information using natural language queries
- **Multi-document Coverage**: Search across all documents simultaneously
- **Context-aware Results**: Results ranked by relevance and context
- **Source Attribution**: Direct links to specific pages and sections
- **Topic Categorization**: Organized by development areas (security, performance, integration, etc.)

## 📊 Monitoring & Analytics Dashboard

### 📈 Real-time Metrics
- **Token Usage Tracking**: Input/output tokens, cost calculations, and model usage breakdown
- **Query Performance**: Response times, retrieval accuracy, and source utilization patterns
- **Function Calling Analytics**: Tool usage frequency, success rates, and execution times
- **RAG Visualization**: Query processing insights, document coverage, and retrieval effectiveness

### 📉 Performance Insights
- **Response Time Analysis**: Query complexity vs. processing time correlations
- **Source Utilization**: Most referenced documents and content gaps
- **User Interaction Patterns**: Common query types and feature usage
- **Cost Optimization**: Token efficiency and model performance comparisons