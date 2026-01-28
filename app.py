import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
from collections import defaultdict

st.set_page_config(
    page_title="🎯 Zoom Attendance Tracker",
    page_icon="📊",
    layout="wide"
)

def get_zoom_token(account_id, client_id, client_secret):
    url = "https://zoom.us/oauth/token"
    data = {'grant_type': 'account_credentials', 'account_id': account_id}
    response = requests.post(url, data=data, auth=(client_id, client_secret))
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def get_daily_meeting_data(token, meeting_id, target_date):
    headers = {'Authorization': f'Bearer {token}'}
    
    # Try instances API first
    instances_url = f"https://api.zoom.us/v2/past_meetings/{meeting_id}/instances"
    params = {'from': target_date, 'to': target_date}
    
    instances_response = requests.get(instances_url, headers=headers, params=params)
    
    all_participants = []
    
    if instances_response.status_code == 200:
        instances_data = instances_response.json()
        meetings = instances_data.get('meetings', [])
        
        for meeting in meetings:
            instance_uuid = meeting.get('uuid')
            
            # Get participants for this instance
            participants_url = f"https://api.zoom.us/v2/report/meetings/{instance_uuid}/participants"
            
            # Handle pagination
            next_page_token = None
            while True:
                params = {'page_size': 300}
                if next_page_token:
                    params['next_page_token'] = next_page_token
                
                participants_response = requests.get(participants_url, headers=headers, params=params)
                
                if participants_response.status_code == 200:
                    participants_data = participants_response.json()
                    participants = participants_data.get('participants', [])
                    all_participants.extend(participants)
                    
                    next_page_token = participants_data.get('next_page_token')
                    if not next_page_token:
                        break
                else:
                    break
    
    # Fallback: Try direct meeting report
    if not all_participants:
        direct_url = f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants"
        
        next_page_token = None
        while True:
            params = {'page_size': 300}
            if next_page_token:
                params['next_page_token'] = next_page_token
            
            direct_response = requests.get(direct_url, headers=headers, params=params)
            
            if direct_response.status_code == 200:
                participants_data = direct_response.json()
                participants = participants_data.get('participants', [])
                all_participants.extend(participants)
                
                next_page_token = participants_data.get('next_page_token')
                if not next_page_token:
                    break
            else:
                break
    
    return all_participants

def parse_env_file(uploaded_file):
    content = uploaded_file.read().decode('utf-8')
    env_vars = {}
    for line in content.split('\n'):
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()
    return env_vars

def convert_to_ist(utc_time_str):
    """Convert UTC time to IST"""
    if not utc_time_str or utc_time_str == '':
        return 'N/A'
    try:
        # Parse UTC time
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        # Convert to IST (+5:30)
        ist_time = utc_time + timedelta(hours=5, minutes=30)
        return ist_time.strftime('%Y-%m-%d %H:%M:%S IST')
    except:
        return utc_time_str

def format_duration(seconds):
    """Convert seconds to minutes"""
    minutes = seconds // 60
    return f"{minutes} min"

# Main App
st.title("🎯 Zoom Attendance Tracker")
st.markdown("### Track participant attendance")

# Sidebar
with st.sidebar:
    st.header("📋 Configuration")
    
    uploaded_file = st.file_uploader("Upload .env file", type=['env'])
    
    if uploaded_file:
        env_vars = parse_env_file(uploaded_file)
        st.success("✅ Environment file loaded!")
        
        meeting_id = st.text_input("Meeting ID", value=env_vars.get('ZOOM_MEETING_ID', ''))
        target_date = st.date_input("Meeting Date", value=datetime.now())
        
        if st.button("🚀 Fetch Attendance Data", type="primary"):
            if meeting_id:
                with st.spinner("Fetching data..."):
                    token = get_zoom_token(
                        env_vars.get('ZOOM_ACCOUNT_ID'),
                        env_vars.get('ZOOM_CLIENT_ID'),
                        env_vars.get('ZOOM_CLIENT_SECRET')
                    )
                    
                    if token:
                        participants = get_daily_meeting_data(
                            token, meeting_id, target_date.strftime('%Y-%m-%d')
                        )
                        
                        if participants:
                            st.session_state['participants'] = participants
                            st.success(f"✅ Found {len(participants)} participants!")
                        else:
                            st.error("❌ No participants found")
                    else:
                        st.error("❌ Authentication failed")
            else:
                st.error("❌ Please enter Meeting ID")

# Main content
if 'participants' in st.session_state:
    participants = st.session_state['participants']
    
    st.write(f"Debug: Total raw participants found: {len(participants)}")
    
    # Remove duplicates based on email (or name if no email)
    unique_participants = {}
    for p in participants:
        email = p.get('user_email', 'N/A')
        name = p.get('name', 'Unknown')
        duration = p.get('duration', 0)
        
        # Use email as primary key, fallback to name
        if email != 'N/A' and email != '':
            key = email
        else:
            key = name
        
        if key not in unique_participants:
            unique_participants[key] = {
                'name': name,
                'email': email,
                'join_time': p.get('join_time', ''),
                'leave_time': p.get('leave_time', ''),
                'duration': duration,
                'max_duration': duration  # Track the longest single session
            }
        else:
            # For duplicates, keep the longest duration (not sum)
            if duration > unique_participants[key]['max_duration']:
                unique_participants[key]['duration'] = duration
                unique_participants[key]['max_duration'] = duration
                unique_participants[key]['join_time'] = p.get('join_time', '')
                unique_participants[key]['leave_time'] = p.get('leave_time', '')
    
    st.write(f"Debug: Unique participants after deduplication: {len(unique_participants)}")
    
    # Create DataFrame from unique participants
    data = []
    for key, p in unique_participants.items():
        duration_seconds = p['duration']
        duration_minutes = duration_seconds // 60  # Convert seconds to minutes
        
        data.append({
            'Name': p['name'],
            'Email': p['email'],
            'Join Time IST': convert_to_ist(p['join_time']),
            'Leave Time IST': convert_to_ist(p['leave_time']),
            'Duration (min)': duration_minutes,
            'Duration': f"{duration_minutes} min"
        })
    
    df = pd.DataFrame(data)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Unique Participants", len(df))
    with col2:
        st.metric("⏱️ Total Hours", f"{df['Duration (min)'].sum() / 60:.1f}")
    with col3:
        st.metric("📊 Avg Duration", f"{int(df['Duration (min)'].mean()) if len(df) > 0 else 0} min")
    with col4:
        st.metric("🏆 Max Duration", f"{df['Duration (min)'].max() if len(df) > 0 else 0} min")
    
    # Chart
    fig = px.bar(df.head(15), x='Name', y='Duration (min)',
                title="📊 Participant Duration",
                color='Duration (min)',
                color_continuous_scale='viridis')
    fig.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig, width='stretch')
    
    # Table
    st.subheader("📋 Detailed Report")
    
    search = st.text_input("🔍 Search participants")
    
    if search:
        filtered_df = df[df['Name'].str.contains(search, case=False, na=False)]
    else:
        filtered_df = df
    
    display_df = filtered_df[['Name', 'Email', 'Duration', 'Join Time IST', 'Leave Time IST']]
    
    st.dataframe(
        display_df,
        width='stretch',
        column_config={
            "Name": st.column_config.TextColumn("👤 Name"),
            "Email": st.column_config.TextColumn("📧 Email"),
            "Duration": st.column_config.TextColumn("⏱️ Duration"),
            "Join Time IST": st.column_config.TextColumn("🟢 Join (IST)"),
            "Leave Time IST": st.column_config.TextColumn("🔴 Leave (IST)")
        }
    )
    
    # Download
    csv = display_df.to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        data=csv,
        file_name=f"zoom_attendance_{target_date}.csv",
        mime="text/csv"
    )

else:
    st.info("👆 Upload your .env file and fetch data to get started!")
    
    st.subheader("📝 Sample .env format:")
    st.code("""
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_MEETING_ID=your_meeting_id
    """, language="bash")