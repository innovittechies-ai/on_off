import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import io

st.set_page_config(
    page_title="🎯 Zoom Attendance Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_zoom_token(account_id, client_id, client_secret):
    """Get Zoom OAuth token"""
    url = "https://zoom.us/oauth/token"
    data = {'grant_type': 'account_credentials', 'account_id': account_id}
    response = requests.post(url, data=data, auth=(client_id, client_secret))
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def get_meeting_instances(token, meeting_id, start_date, end_date):
    """Get all meeting instances in date range"""
    headers = {'Authorization': f'Bearer {token}'}
    
    # Try instances API first
    instances_url = f"https://api.zoom.us/v2/past_meetings/{meeting_id}/instances"
    params = {'from': start_date, 'to': end_date}
    
    response = requests.get(instances_url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('meetings', [])
    
    # Fallback to single meeting
    meeting_url = f"https://api.zoom.us/v2/report/meetings/{meeting_id}"
    response = requests.get(meeting_url, headers=headers)
    if response.status_code == 200:
        meeting_data = response.json()
        return [{'uuid': meeting_id, 'start_time': meeting_data.get('start_time')}]
    
    return []

def get_participants(token, meeting_uuid):
    """Get participants for a meeting"""
    headers = {'Authorization': f'Bearer {token}'}
    participants_url = f"https://api.zoom.us/v2/report/meetings/{meeting_uuid}/participants"
    
    all_participants = []
    next_page_token = None
    
    while True:
        params = {'page_size': 300}
        if next_page_token:
            params['next_page_token'] = next_page_token
        
        response = requests.get(participants_url, headers=headers, params=params)
        if response.status_code != 200:
            break
        
        data = response.json()
        participants = data.get('participants', [])
        all_participants.extend(participants)
        
        next_page_token = data.get('next_page_token')
        if not next_page_token:
            break
    
    return all_participants

def parse_env_file(uploaded_file):
    """Parse uploaded .env file"""
    content = uploaded_file.read().decode('utf-8')
    env_vars = {}
    for line in content.split('\n'):
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()
    return env_vars

# Main App
st.title("🎯 Zoom Attendance Tracker")
st.markdown("### Track participant attendance across multiple sessions")

# Sidebar for inputs
with st.sidebar:
    st.header("📋 Configuration")
    
    # Upload .env file
    uploaded_file = st.file_uploader("Upload .env file", type=['env'])
    
    if uploaded_file:
        env_vars = parse_env_file(uploaded_file)
        st.success("✅ Environment file loaded!")
        
        # Meeting ID input
        meeting_id = st.text_input("Meeting ID", value=env_vars.get('ZOOM_MEETING_ID', ''))
        
        # Date range
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
        with col2:
            end_date = st.date_input("End Date", value=datetime.now())
        
        # Fetch button
        if st.button("🚀 Fetch Attendance Data", type="primary"):
            if meeting_id:
                with st.spinner("Fetching data..."):
                    # Get token
                    token = get_zoom_token(
                        env_vars.get('ZOOM_ACCOUNT_ID'),
                        env_vars.get('ZOOM_CLIENT_ID'),
                        env_vars.get('ZOOM_CLIENT_SECRET')
                    )
                    
                    if token:
                        # Get meeting instances
                        instances = get_meeting_instances(
                            token, meeting_id, 
                            start_date.strftime('%Y-%m-%d'),
                            end_date.strftime('%Y-%m-%d')
                        )
                        
                        if instances:
                            st.session_state['attendance_data'] = []
                            
                            for instance in instances:
                                participants = get_participants(token, instance['uuid'])
                                for p in participants:
                                    st.session_state['attendance_data'].append({
                                        'name': p.get('name', 'Unknown'),
                                        'email': p.get('user_email', 'N/A'),
                                        'join_time': p.get('join_time', ''),
                                        'leave_time': p.get('leave_time', ''),
                                        'duration': p.get('duration', 0),
                                        'meeting_date': instance['start_time'][:10] if instance.get('start_time') else 'Unknown'
                                    })
                            
                            st.success(f"✅ Found {len(st.session_state['attendance_data'])} attendance records!")
                        else:
                            st.error("❌ No meeting data found for the selected date range")
                    else:
                        st.error("❌ Failed to authenticate with Zoom API")
            else:
                st.error("❌ Please enter a Meeting ID")

# Main content
if 'attendance_data' in st.session_state and st.session_state['attendance_data']:
    df = pd.DataFrame(st.session_state['attendance_data'])
    
    # Process data for unique users
    user_summary = defaultdict(lambda: {'total_duration': 0, 'sessions': [], 'email': 'N/A'})
    
    for _, row in df.iterrows():
        key = row['email'] if row['email'] != 'N/A' else row['name']
        user_summary[key]['total_duration'] += row['duration']
        user_summary[key]['sessions'].append({
            'date': row['meeting_date'],
            'duration': row['duration'],
            'join_time': row['join_time'],
            'leave_time': row['leave_time']
        })
        user_summary[key]['email'] = row['email']
        user_summary[key]['name'] = row['name']
    
    # Create summary DataFrame
    summary_data = []
    for user_key, data in user_summary.items():
        summary_data.append({
            'Name': data['name'],
            'Email': data['email'],
            'Total Duration (min)': data['total_duration'],
            'Total Sessions': len(data['sessions']),
            'Avg Duration/Session': round(data['total_duration'] / len(data['sessions']), 1),
            'Sessions': data['sessions']
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Participants", len(summary_df))
    
    with col2:
        st.metric("📅 Total Sessions", len(df['meeting_date'].unique()))
    
    with col3:
        st.metric("⏱️ Total Hours", f"{summary_df['Total Duration (min)'].sum() / 60:.1f}")
    
    with col4:
        st.metric("📊 Avg Duration/Person", f"{summary_df['Total Duration (min)'].mean():.1f} min")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Duration distribution
        fig = px.histogram(summary_df, x='Total Duration (min)', 
                          title="📊 Duration Distribution",
                          color_discrete_sequence=['#FF6B6B'])
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        # Sessions per user
        fig = px.bar(summary_df.head(10), x='Name', y='Total Sessions',
                    title="🏆 Top 10 Most Active Participants",
                    color='Total Sessions',
                    color_continuous_scale='viridis')
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, width='stretch')
    
    # Detailed table
    st.subheader("📋 Detailed Attendance Report")
    
    # Search functionality
    search_term = st.text_input("🔍 Search participants", placeholder="Enter name or email...")
    
    if search_term:
        filtered_df = summary_df[
            summary_df['Name'].str.contains(search_term, case=False, na=False) |
            summary_df['Email'].str.contains(search_term, case=False, na=False)
        ]
    else:
        filtered_df = summary_df
    
    # Display table without Sessions column for cleaner view
    display_df = filtered_df.drop('Sessions', axis=1)
    st.dataframe(
        display_df,
        width='stretch',
        column_config={
            "Name": st.column_config.TextColumn("👤 Name", width="medium"),
            "Email": st.column_config.TextColumn("📧 Email", width="medium"),
            "Total Duration (min)": st.column_config.NumberColumn("⏱️ Duration", format="%d min"),
            "Total Sessions": st.column_config.NumberColumn("📅 Sessions"),
            "Avg Duration/Session": st.column_config.NumberColumn("📊 Avg/Session", format="%.1f min")
        }
    )
    
    # Expandable session details
    st.subheader("📅 Session-wise Details")
    
    selected_user = st.selectbox("Select participant for detailed view:", 
                                options=filtered_df['Name'].tolist())
    
    if selected_user:
        user_sessions = filtered_df[filtered_df['Name'] == selected_user]['Sessions'].iloc[0]
        
        sessions_df = pd.DataFrame(user_sessions)
        sessions_df['join_time'] = sessions_df['join_time'].apply(
            lambda x: x.split('T')[1][:8] if 'T' in str(x) else str(x)
        )
        sessions_df['leave_time'] = sessions_df['leave_time'].apply(
            lambda x: x.split('T')[1][:8] if 'T' in str(x) else 'N/A'
        )
        
        st.dataframe(
            sessions_df,
            width='stretch',
            column_config={
                "date": st.column_config.DateColumn("📅 Date"),
                "duration": st.column_config.NumberColumn("⏱️ Duration (min)"),
                "join_time": st.column_config.TextColumn("🟢 Join Time"),
                "leave_time": st.column_config.TextColumn("🔴 Leave Time")
            }
        )
    
    # Download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Report as CSV",
        data=csv,
        file_name=f"zoom_attendance_{start_date}_{end_date}.csv",
        mime="text/csv"
    )

else:
    st.info("👆 Please upload your .env file and configure the settings in the sidebar to get started!")
    
    # Sample .env file format
    st.subheader("📝 Sample .env file format:")
    st.code("""
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_MEETING_ID=your_meeting_id
    """, language="bash")