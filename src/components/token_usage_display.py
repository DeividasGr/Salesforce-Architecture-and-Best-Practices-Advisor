import streamlit as st
import plotly.express as px
import pandas as pd
import json
from datetime import datetime
from src.token_tracker import token_tracker

def render_token_usage_sidebar():
    """Render token usage summary in sidebar"""
    with st.sidebar:
        st.header("💰 Token Usage")
        
        stats = token_tracker.get_session_stats()
        
        if stats['query_count'] == 0:
            st.info("No queries processed yet.")
            return
        
        # Key metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Queries", 
                stats['query_count'],
                help="Total number of LLM calls this session"
            )
        with col2:
            st.metric(
                "Total Cost", 
                f"${stats['total_cost']:.4f}",
                help="Estimated cost based on current model pricing"
            )
        
        # Token breakdown
        total_tokens = stats['total_input_tokens'] + stats['total_output_tokens']
        st.metric(
            "Total Tokens",
            f"{total_tokens:,}",
            help=f"Input: {stats['total_input_tokens']:,} | Output: {stats['total_output_tokens']:,}"
        )
        
        # Average costs
        if stats['query_count'] > 0:
            avg_cost = stats['total_cost'] / stats['query_count']
            avg_tokens = total_tokens / stats['query_count']
            
            st.caption(f"**Avg per query:** ${avg_cost:.4f} • {avg_tokens:.0f} tokens")
        
        # Quick cost visualization
        if len(stats['detailed_calls']) > 1:
            recent_costs = [call['cost'] for call in stats['detailed_calls'][-10:]]
            fig = px.line(
                y=recent_costs,
                title="Cost Trend (Last 10)",
                labels={'y': 'Cost ($)', 'index': 'Query'}
            )
            fig.update_layout(height=200, showlegend=False)
            fig.update_traces(line_color='#1f77b4')
            st.plotly_chart(fig, use_container_width=True)
        
        # Reset button
        if st.button("🔄 Reset Usage", help="Reset token usage statistics"):
            token_tracker.reset_session_stats()
            st.rerun()

def render_detailed_token_dashboard():
    """Render detailed token usage dashboard"""
    # Back button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.show_token_dashboard = False
            st.rerun()
    
    st.title("💰 Token Usage & Cost Analysis")
    
    stats = token_tracker.get_session_stats()
    
    if stats['query_count'] == 0:
        st.info("No token usage data available yet. Start asking questions to see usage statistics!")
        return
    
    # Session overview
    st.subheader("📊 Session Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Total Queries",
            stats['query_count'],
            help="Number of LLM API calls made"
        )
    with col2:
        st.metric(
            "Total Cost",
            f"${stats['total_cost']:.4f}",
            help="Estimated cost based on model pricing"
        )
    with col3:
        total_tokens = stats['total_input_tokens'] + stats['total_output_tokens']
        st.metric(
            "Total Tokens",
            f"{total_tokens:,}",
            help="Combined input and output tokens"
        )
    with col4:
        session_start = datetime.fromisoformat(stats['session_start'])
        duration = datetime.now() - session_start
        hours = duration.total_seconds() / 3600
        st.metric(
            "Session Duration",
            f"{hours:.1f}h",
            help=f"Started: {session_start.strftime('%H:%M')}"
        )
    
    # Token breakdown charts
    st.subheader("🔍 Token Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Input vs Output tokens pie chart
        if stats['total_input_tokens'] > 0 or stats['total_output_tokens'] > 0:
            token_data = pd.DataFrame({
                'Type': ['Input Tokens', 'Output Tokens'],
                'Count': [stats['total_input_tokens'], stats['total_output_tokens']]
            })
            
            fig = px.pie(
                token_data, 
                values='Count', 
                names='Type',
                title="Token Distribution",
                color_discrete_map={
                    'Input Tokens': '#2E86AB',
                    'Output Tokens': '#A23B72'
                }
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Model usage breakdown
        if stats['model_usage']:
            model_data = []
            for model, usage in stats['model_usage'].items():
                model_data.append({
                    'Model': model,
                    'Calls': usage['calls'],
                    'Cost': usage['cost'],
                    'Tokens': usage['input_tokens'] + usage['output_tokens']
                })
            
            if model_data:
                model_df = pd.DataFrame(model_data)
                
                fig = px.bar(
                    model_df,
                    x='Model',
                    y='Cost',
                    title="Cost by Model",
                    color='Calls',
                    color_continuous_scale='viridis'
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
    
    # Detailed call history
    if stats['detailed_calls']:
        st.subheader("📝 Recent API Calls")
        
        # Create DataFrame from detailed calls
        calls_data = []
        for i, call in enumerate(reversed(stats['detailed_calls'][-20:])):  # Last 20 calls
            calls_data.append({
                'Call #': len(stats['detailed_calls']) - i,
                'Time': datetime.fromisoformat(call['timestamp']).strftime('%H:%M:%S'),
                'Model': call['model'],
                'Input Tokens': call['input_tokens'],
                'Output Tokens': call['output_tokens'],
                'Total Tokens': call['total_tokens'],
                'Cost': f"${call['cost']:.4f}",
                'Response Time': f"{call['response_time']:.2f}s",
                'Estimated': '⚠️' if call.get('estimated', False) else '✅'
            })
        
        calls_df = pd.DataFrame(calls_data)
        st.dataframe(
            calls_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Estimated': st.column_config.TextColumn(
                    'Accuracy',
                    help="✅ = Exact count, ⚠️ = Estimated"
                )
            }
        )
        
        # Usage trends over time
        st.subheader("📈 Usage Trends")
        
        if len(stats['detailed_calls']) > 1:
            trend_data = []
            cumulative_cost = 0
            cumulative_tokens = 0
            
            for i, call in enumerate(stats['detailed_calls']):
                cumulative_cost += call['cost']
                cumulative_tokens += call['total_tokens']
                
                trend_data.append({
                    'Query': i + 1,
                    'Cost': call['cost'],
                    'Cumulative Cost': cumulative_cost,
                    'Tokens': call['total_tokens'],
                    'Cumulative Tokens': cumulative_tokens,
                    'Timestamp': call['timestamp']
                })
            
            trend_df = pd.DataFrame(trend_data)
            
            # Cost and token trends
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.line(
                    trend_df,
                    x='Query',
                    y='Cumulative Cost',
                    title="Cumulative Cost Over Time",
                    labels={'Cumulative Cost': 'Cost ($)'}
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.scatter(
                    trend_df,
                    x='Query',
                    y='Tokens',
                    title="Tokens per Query",
                    labels={'Tokens': 'Token Count'},
                    color='Cost',
                    size='Cost',
                    color_continuous_scale='viridis'
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
    
    # Cost projection
    if stats['query_count'] > 5:
        st.subheader("🔮 Cost Projection")
        
        avg_cost_per_query = stats['total_cost'] / stats['query_count']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Next 10 Queries",
                f"${avg_cost_per_query * 10:.4f}",
                help="Estimated cost for 10 more queries at current rate"
            )
        with col2:
            st.metric(
                "Next 100 Queries",
                f"${avg_cost_per_query * 100:.3f}",
                help="Estimated cost for 100 more queries at current rate"
            )
        with col3:
            daily_estimate = avg_cost_per_query * 50  # Assume 50 queries per day
            st.metric(
                "Daily Estimate",
                f"${daily_estimate:.3f}",
                help="Estimated daily cost at ~50 queries/day"
            )
    
    # Export usage data
    st.subheader("📤 Export Usage Data")
    
    # Prepare usage report data
    usage_report = {
        'session_summary': stats,
        'export_timestamp': datetime.now().isoformat(),
        'detailed_calls': stats['detailed_calls']
    }
    
    # Create JSON data
    json_data = json.dumps(usage_report, indent=2)
    
    # Direct download button
    st.download_button(
        "📊 Download Usage Report (JSON)",
        data=json_data,
        file_name=f"token_usage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        help="Download detailed token usage report as JSON file",
        use_container_width=True
    )