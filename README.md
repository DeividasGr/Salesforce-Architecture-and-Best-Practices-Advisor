# Salesforce Architecture & Best Practices Advisor

A specialized RAG chatbot built with Streamlit and LangChain that provides expert guidance on Salesforce development, architecture, and best practices using official documentation.

## 🚀 Features

### Core Functionality
- **Advanced RAG Implementation**: ChromaDB vector store with Google Gemini embeddings
- **Function Calling**: 3 specialized tools for Salesforce development
  - Apex Code Reviewer
  - SOQL Query Optimizer  
  - Governor Limits Calculator
- **Domain Expertise**: Focused on Salesforce architecture and best practices
- **Real-time Processing**: Direct document upload and processing

### Advanced Features
- **Conversation History**: Full conversation tracking with export capabilities
- **RAG Visualization**: Interactive dashboards showing query analysis
- **Token Usage Tracking**: Real-time cost monitoring and analytics
- **Multi-format Export**: JSON, CSV, Markdown, PDF export options
- **Source Citations**: Detailed source attribution with document metadata

## 🛠️ Technical Stack

- **Frontend**: Streamlit
- **LLM**: Google Gemini 2.0 Flash
- **Vector Database**: ChromaDB
- **Embeddings**: Google Generative AI (text-embedding-004)
- **Framework**: LangChain
- **Monitoring**: LangSmith integration

## 📦 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd salesforce-rag-advisor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   GOOGLE_API_KEY=your_google_api_key_here
   STREAMLIT_FAST_MODE=1
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

### Cloud Deployment (Streamlit Cloud)

1. **Push to GitHub**: Ensure your code is in a GitHub repository
2. **Connect to Streamlit Cloud**: Visit [share.streamlit.io](https://share.streamlit.io)
3. **Configure Secrets**: Add `GOOGLE_API_KEY` in the secrets section
4. **Deploy**: Your app will be available at `https://your-app-name.streamlit.app`

## 🔧 Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Your Google AI API key (required)
- `STREAMLIT_FAST_MODE`: Set to "1" for faster loading (optional)

### Scaling Considerations
- **Vector Store**: ChromaDB persists data locally; consider hosted solutions for high traffic
- **Rate Limiting**: Built-in rate limiting (10/minute, 100/hour per user)
- **Memory Management**: Efficient document chunking and caching strategies
- **Cost Management**: Token usage tracking and optimization

## 📚 Knowledge Base

The system includes comprehensive Salesforce documentation:
- Apex Developer Guide
- Security Implementation Guide
- Integration Patterns & Practices
- Salesforce DX Developer Guide
- SOQL and SOSL Reference
- Metadata API Guide
- REST API Guide
- App Limits Cheat Sheet
- Platform Events Guide

## 🔍 Function Calling Examples

### Apex Code Review
```
Please review this Apex code:
public class AccountProcessor {
    public void processAccounts() {
        for(Account acc : [SELECT Id, Name FROM Account]) {
            acc.Name = acc.Name + ' - Updated';
            update acc;
        }
    }
}
```

### SOQL Optimization
```
Can you optimize this SOQL query?
SELECT Id, Name, Owner.Name, CreatedBy.Name FROM Account WHERE Name LIKE '%test%' ORDER BY CreatedDate
```

### Governor Limits Calculation
```
Calculate governor limits usage for these operations:
{"soql_queries": 85, "dml_statements": 140, "heap_size_mb": 5}
```

## 🏗️ Architecture

```
User Query → Input Validation → Function Detection → RAG Retrieval → LLM Processing → Response + Sources
                ↓
           Rate Limiting
                ↓
           Token Tracking
                ↓
           Conversation History
```

## 📊 Monitoring & Analytics

- **Real-time Token Usage**: Track costs and usage patterns
- **Query Analytics**: Response times, source utilization
- **Function Calling Metrics**: Tool usage statistics
- **RAG Visualization**: Query processing insights

## 🔒 Security Features

- Input validation and sanitization
- Rate limiting per user session
- XSS and injection protection
- Secure API key management
- Error handling without information leakage

## 🚀 Performance Optimizations

- Persistent vector store with smart loading
- Efficient document chunking strategies
- Session-based caching
- Optimized embedding retrieval
- Fast mode for production environments

## 📈 Scaling Recommendations

### For Production Use:
1. **Database**: Migrate to hosted ChromaDB or Pinecone
2. **Authentication**: Implement user authentication system
3. **Load Balancing**: Use multiple Streamlit instances
4. **Caching**: Add Redis for session management
5. **Monitoring**: Enhanced analytics and alerting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Salesforce for comprehensive documentation
- LangChain community for the RAG framework
- Streamlit for the amazing web app framework
- Google for the Gemini AI models