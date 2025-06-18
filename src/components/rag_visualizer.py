import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import time
from typing import Dict, List, Any

class SimpleRAGVisualizer:
    def __init__(self):
        # Initialize session state for tracking
        if 'query_stats' not in st.session_state:
            st.session_state.query_stats = []
    
    def track_query(self, query: str, result: Dict[str, Any], response_time: float):
        """Track a query and its results"""
        stats = {
            'timestamp': time.time(),
            'query': query[:50] + "..." if len(query) > 50 else query,
            'response_time': response_time,
            'sources_count': len(result.get('sources', [])),
            'tool_used': result.get('tool_used', 'Regular RAG'),
            'answer_length': len(result.get('answer', ''))
        }
        st.session_state.query_stats.append(stats)
        
        # Keep only last 50 queries
        if len(st.session_state.query_stats) > 50:
            st.session_state.query_stats.pop(0)
    
    def show_current_query_viz(self, result: Dict[str, Any]):
        """Show visualization for current query"""
        if not result:
            return
        
        st.subheader("📊 Current Query Analysis")
        
        # Quick metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sources Used", len(result.get('sources', [])))
        with col2:
            st.metric("Response Length", f"{len(result.get('answer', ''))} chars")
        with col3:
            tool = result.get('tool_used', 'Regular RAG')
            st.metric("Tool Used", "Function" if tool != 'Regular RAG' else "RAG")
        
        # Sources breakdown
        sources = result.get('sources', [])
        if sources:
            source_files = [doc.metadata.get('source_file', 'Unknown') for doc in sources]
            source_df = pd.DataFrame({'Source': source_files})
            source_counts = source_df['Source'].value_counts()
            
            fig = px.pie(values=source_counts.values, names=source_counts.index, 
                        title="Sources Used in Response")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    def show_history_dashboard(self):
        """Show simple dashboard of query history"""
        if not st.session_state.query_stats:
            st.info("No query history available yet.")
            return
        
        st.subheader("📈 Query History Dashboard")
        
        df = pd.DataFrame(st.session_state.query_stats)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Queries", len(df))
        with col2:
            st.metric("Avg Response Time", f"{df['response_time'].mean():.2f}s")
        with col3:
            st.metric("Avg Sources", f"{df['sources_count'].mean():.1f}")
        with col4:
            function_calls = len(df[df['tool_used'] != 'Regular RAG'])
            st.metric("Function Calls", function_calls)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Response times
            fig1 = px.line(df.tail(20), y='response_time', 
                          title="Response Time Trend (Last 20)")
            fig1.update_layout(height=300)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Tool usage
            tool_counts = df['tool_used'].value_counts()
            fig2 = px.bar(x=tool_counts.index, y=tool_counts.values,
                         title="Tool Usage")
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

def show_simple_flow():
    """Show simple RAG process flow"""
    st.subheader("🔄 RAG Process Flow")
    
    # Simple flow diagram using columns
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown("### 📝\n**Query Input**")
    with col2:
        st.markdown("### 🔍\n**Search Docs**")
    with col3:
        st.markdown("### 📚\n**Retrieve Context**")
    with col4:
        st.markdown("### 🤖\n**LLM Process**")
    with col5:
        st.markdown("### ✅\n**Generate Answer**")
    
    # Add flow description
    st.markdown("---")
    st.markdown("**Process:** Query → Vector Search → Context Building → AI Processing → Response")

def add_visualization_to_sidebar():
    """Add simple visualization toggle to sidebar"""
    with st.sidebar:
        st.header("📊 Visualization")
        show_viz = st.checkbox("Show Query Visualization", value=True)
        
        # Store in session state so it's accessible everywhere
        st.session_state.show_query_viz = show_viz
        
        if show_viz and st.button("📈 View Dashboard"):
            st.session_state.show_dashboard = True
        
        return show_viz

def render_simple_rag_viz():
    """Render the visualization dashboard page"""
    st.title("📊 RAG System Dashboard")
    
    # Add tabs for different views
    tab1, tab2 = st.tabs(["📈 Statistics", "🔄 Process Flow"])
    
    with tab1:
        visualizer = SimpleRAGVisualizer()
        visualizer.show_history_dashboard()
        
        # Clear history button
        if st.button("🗑️ Clear History"):
            st.session_state.query_stats = []
            st.success("History cleared!")
            st.rerun()
    
    with tab2:
        show_simple_flow()