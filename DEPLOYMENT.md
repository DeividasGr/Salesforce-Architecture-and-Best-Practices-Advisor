# Streamlit Cloud Deployment Guide

## Prerequisites

1. **GitHub Repository**: Code must be in a public GitHub repository
2. **Google AI API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
3. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)

## Step-by-Step Deployment

### 1. Prepare Repository

Ensure your repository contains:
- ✅ `app.py` (main Streamlit application)
- ✅ `requirements.txt` (dependencies)
- ✅ `.streamlit/config.toml` (Streamlit configuration)
- ✅ All source code in `src/` directory
- ✅ PDF documents in `data/raw/` directory

### 2. Push to GitHub

```bash
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

### 3. Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "Create app"
4. Select your repository
5. Set main file path: `app.py`
6. Choose branch: `main`

### 4. Configure Secrets

In Streamlit Cloud dashboard:
1. Go to your app settings
2. Click "Secrets" tab
3. Add the following:

```toml
GOOGLE_API_KEY = "your_actual_google_api_key_here"
STREAMLIT_FAST_MODE = "1"
```

### 5. Deploy

Click "Deploy!" and wait for the build to complete.

## Environment Configuration

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google AI API key for Gemini models | Yes |
| `STREAMLIT_FAST_MODE` | Skip file watcher for faster startup | No |

### Optional Configuration

```toml
# .streamlit/secrets.toml (for cloud deployment)
[secrets]
GOOGLE_API_KEY = "your-key"
STREAMLIT_FAST_MODE = "1"

# Additional optional settings
LANGCHAIN_API_KEY = "your-langsmith-key"  # For enhanced monitoring
LANGCHAIN_PROJECT = "salesforce-rag-prod"
```

## Scaling Considerations

### Performance Optimization

1. **Fast Mode**: Enable `STREAMLIT_FAST_MODE=1` to skip file watcher initialization
2. **Resource Limits**: Streamlit Cloud provides:
   - 1 GB RAM
   - 2 CPU cores
   - 1 app per account (free tier)

### Resource Management

1. **Vector Store**: 
   - Current: Local ChromaDB storage
   - Recommendation: For production, consider hosted vector DB

2. **Memory Usage**:
   - Document chunks are loaded efficiently
   - Vector store persists between sessions
   - Rate limiting prevents overload

3. **Cost Monitoring**:
   - Built-in token tracking
   - Google AI API costs monitored in real-time

### High-Traffic Recommendations

If expecting high traffic, consider:

1. **Streamlit Cloud Teams/Enterprise**: 
   - More resources
   - Multiple apps
   - Custom domains

2. **Alternative Hosting**:
   - Docker deployment on cloud platforms
   - Kubernetes for auto-scaling

3. **Database Migration**:
   - Move to hosted ChromaDB
   - Use Pinecone or Weaviate for production

## Monitoring & Maintenance

### Built-in Monitoring

- ✅ Token usage tracking with costs
- ✅ Query performance metrics
- ✅ Error logging and handling
- ✅ Rate limiting statistics

### Health Checks

The app includes:
- Automatic error recovery
- Graceful handling of API failures
- User-friendly error messages
- Session state management

### Updates

To update the deployed app:
1. Push changes to GitHub main branch
2. Streamlit Cloud auto-deploys within minutes
3. Monitor deployment in Streamlit Cloud dashboard

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check `requirements.txt` for correct package versions
   - Verify Python version compatibility (3.8-3.11)

2. **API Key Issues**:
   - Ensure `GOOGLE_API_KEY` is set in secrets
   - Check API key validity and quotas

3. **Memory Issues**:
   - Monitor resource usage in Streamlit Cloud
   - Consider optimizing document processing

4. **Import Errors**:
   - Verify all dependencies in `requirements.txt`
   - Check for relative import issues

### Debug Mode

Enable debug information by setting:
```toml
[client]
showErrorDetails = true
```

## Security Best Practices

### Secrets Management

- ✅ Never commit API keys to repository
- ✅ Use Streamlit Cloud secrets for sensitive data
- ✅ Regularly rotate API keys

### Application Security

- ✅ Input validation implemented
- ✅ Rate limiting in place
- ✅ Error handling without information leakage
- ✅ XSS protection through Streamlit

## Cost Optimization

### Google AI API Costs

- **Gemini 2.0 Flash**: ~$0.15/1M input tokens, ~$0.60/1M output tokens
- **Embeddings**: ~$0.10/1M tokens
- **Built-in tracking**: Monitor costs in real-time

### Streamlit Cloud Costs

- **Free Tier**: 1 public app
- **Teams**: $20/month for private apps and more resources
- **Enterprise**: Custom pricing for advanced features

## Support

For deployment issues:
1. Check [Streamlit Cloud documentation](https://docs.streamlit.io/streamlit-community-cloud)
2. Visit [Streamlit Community Forum](https://discuss.streamlit.io/)
3. Review app logs in Streamlit Cloud dashboard