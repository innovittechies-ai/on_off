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

def get_all_meetings_for_date(token, target_date):
    """Get all meetings for a specific date"""
    headers = {'Authorization': f'Bearer {token}'}
    all_meetings = []
    
    # Try to get past meetings
    past_meetings_url = f"https://api.zoom.us/v2/users/me/meetings"
    params = {'type': 'previous_meetings', 'page_size': 300}
    
    response = requests.get(past_meetings_url, headers=headers, params=params)
    if response.status_code == 200:
        meetings_data = response.json()
        meetings = meetings_data.get('meetings', [])
        
        for meeting in meetings:
            start_time = meeting.get('start_time', '')
            if start_time and start_time[:10] == target_date:
                all_meetings.append(meeting)
    
    return all_meetings

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

def get_participants_with_time_filter(token, meeting_id, start_time_filter=None, end_time_filter=None):
    """Get participants with optional time filtering"""
    participants = get_daily_meeting_data(token, meeting_id, '')
    
    if not start_time_filter and not end_time_filter:
        return participants
    
    filtered_participants = []
    for p in participants:
        join_time_str = p.get('join_time', '')
        if join_time_str:
            try:
                join_time = datetime.fromisoformat(join_time_str.replace('Z', '+00:00'))
                join_time_ist = join_time + timedelta(hours=5, minutes=30)
                join_hour_min = join_time_ist.time()
                
                # Check time filters
                if start_time_filter and join_hour_min < start_time_filter:
                    continue
                if end_time_filter and join_hour_min > end_time_filter:
                    continue
                    
                filtered_participants.append(p)
            except:
                filtered_participants.append(p)  # Include if time parsing fails
        else:
            filtered_participants.append(p)  # Include if no join time
    
    return filtered_participants

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
st.markdown("### Smart Analytics Dashboard")

# Sidebar
with st.sidebar:
    st.header("📅 Smart Analytics")
    
    uploaded_file = st.file_uploader("Upload .env file", type=['env'])
    
    if uploaded_file:
        env_vars = parse_env_file(uploaded_file)
        st.success("✅ Environment file loaded!")
        
        # Analytics mode selection
        mode = st.radio(
            "Select Mode:",
            ["Single Meeting", "Day-wise Analytics"]
        )
        
        if mode == "Single Meeting":
            meeting_id = st.text_input("Meeting ID", value=env_vars.get('ZOOM_MEETING_ID', ''))
            target_date = st.date_input("Meeting Date", value=datetime.now())
            
            # Optional time filters
            st.subheader("⏰ Time Filters (Optional)")
            use_time_filter = st.checkbox("Enable time filtering")
            
            start_time_filter = None
            end_time_filter = None
            
            if use_time_filter:
                col1, col2 = st.columns(2)
                with col1:
                    start_time_filter = st.time_input("Start Time (IST)", value=datetime.strptime("09:00", "%H:%M").time())
                with col2:
                    end_time_filter = st.time_input("End Time (IST)", value=datetime.strptime("18:00", "%H:%M").time())
            
            if st.button("🚀 Fetch Single Meeting Data", type="primary"):
                if meeting_id:
                    with st.spinner("Fetching data..."):
                        token = get_zoom_token(
                            env_vars.get('ZOOM_ACCOUNT_ID'),
                            env_vars.get('ZOOM_CLIENT_ID'),
                            env_vars.get('ZOOM_CLIENT_SECRET')
                        )
                        
                        if token:
                            participants = get_participants_with_time_filter(
                                token, meeting_id, start_time_filter, end_time_filter
                            )
                            
                            if participants:
                                st.session_state['participants'] = participants
                                st.session_state['mode'] = 'single'
                                st.success(f"✅ Found {len(participants)} participants!")
                            else:
                                st.error("❌ No participants found")
                        else:
                            st.error("❌ Authentication failed")
                else:
                    st.error("❌ Please enter Meeting ID")
        
        else:  # Day-wise Analytics
            target_date = st.date_input("Select Date", value=datetime.now())
            
            # Optional time filters
            st.subheader("⏰ Time Filters (Optional)")
            use_time_filter = st.checkbox("Enable time filtering", key="day_time_filter")
            
            start_time_filter = None
            end_time_filter = None
            
            if use_time_filter:
                col1, col2 = st.columns(2)
                with col1:
                    start_time_filter = st.time_input("Start Time (IST)", value=datetime.strptime("09:00", "%H:%M").time(), key="day_start")
                with col2:
                    end_time_filter = st.time_input("End Time (IST)", value=datetime.strptime("18:00", "%H:%M").time(), key="day_end")
            
            if st.button("📈 Fetch Day-wise Analytics", type="primary"):
                with st.spinner("Fetching all meetings for the day..."):
                    token = get_zoom_token(
                        env_vars.get('ZOOM_ACCOUNT_ID'),
                        env_vars.get('ZOOM_CLIENT_ID'),
                        env_vars.get('ZOOM_CLIENT_SECRET')
                    )
                    
                    if token:
                        # Get all meetings for the date
                        meetings = get_all_meetings_for_date(token, target_date.strftime('%Y-%m-%d'))
                        
                        if meetings:
                            st.write(f"Found {len(meetings)} meetings on {target_date}")
                            
                            all_participants = []
                            for meeting in meetings:
                                meeting_id = meeting.get('id')
                                st.write(f"Processing meeting: {meeting.get('topic', 'Unknown')} (ID: {meeting_id})")
                                
                                participants = get_participants_with_time_filter(
                                    token, str(meeting_id), start_time_filter, end_time_filter
                                )
                                all_participants.extend(participants)
                            
                            if all_participants:
                                st.session_state['participants'] = all_participants
                                st.session_state['mode'] = 'daywise'
                                st.success(f"✅ Found {len(all_participants)} total participants across all meetings!")
                            else:
                                st.error("❌ No participants found in any meetings")
                        else:
                            st.error(f"❌ No meetings found for {target_date}")
                    else:
                        st.error("❌ Authentication failed")

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
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Unique Participants", len(df))
    with col2:
        st.metric("📊 Avg Duration", f"{int(df['Duration (min)'].mean()) if len(df) > 0 else 0} min")
    with col3:
        st.metric("🏆 Max Duration", f"{df['Duration (min)'].max() if len(df) > 0 else 0} min")
    
    # Analytics Dashboard
    st.subheader("📊 Attendance Analytics")
    
    # Create analytics tabs
    tab1, tab2, tab3 = st.tabs(["📈 Duration Analysis", "👥 Participation Overview", "⏰ Time Analysis"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Duration distribution bar chart
            fig_duration = px.bar(
                df.sort_values('Duration (min)', ascending=False).head(20), 
                x='Name', y='Duration (min)',
                title="🏆 Top 20 Participants by Duration",
                color='Duration (min)',
                color_continuous_scale='Blues'
            )
            fig_duration.update_layout(xaxis_tickangle=45, height=400)
            st.plotly_chart(fig_duration, width='stretch')
        
        with col2:
            # Duration histogram
            fig_hist = px.histogram(
                df, x='Duration (min)', 
                nbins=10,
                title="📊 Duration Distribution",
                color_discrete_sequence=['#FF6B6B']
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, width='stretch')
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Attendance categories
            duration_categories = []
            for _, row in df.iterrows():
                duration = row['Duration (min)']
                if duration >= 90:
                    duration_categories.append('Full Attendance (90+ min)')
                elif duration >= 60:
                    duration_categories.append('Good Attendance (60-89 min)')
                elif duration >= 30:
                    duration_categories.append('Partial Attendance (30-59 min)')
                else:
                    duration_categories.append('Brief Attendance (<30 min)')
            
            category_counts = pd.Series(duration_categories).value_counts()
            
            fig_pie = px.pie(
                values=category_counts.values, 
                names=category_counts.index,
                title="🎯 Attendance Categories",
                color_discrete_sequence=['#2E8B57', '#4682B4', '#FF8C00', '#DC143C']
            )
            st.plotly_chart(fig_pie, width='stretch')
        
        with col2:
            # Attendance stats
            st.markdown("### 📈 Key Statistics")
            
            full_attendance = len([d for d in df['Duration (min)'] if d >= 90])
            good_attendance = len([d for d in df['Duration (min)'] if 60 <= d < 90])
            partial_attendance = len([d for d in df['Duration (min)'] if 30 <= d < 60])
            brief_attendance = len([d for d in df['Duration (min)'] if d < 30])
            
            st.metric("🟢 Full Attendance (90+ min)", f"{full_attendance} ({full_attendance/len(df)*100:.1f}%)")
            st.metric("🔵 Good Attendance (60-89 min)", f"{good_attendance} ({good_attendance/len(df)*100:.1f}%)")
            st.metric("🟡 Partial Attendance (30-59 min)", f"{partial_attendance} ({partial_attendance/len(df)*100:.1f}%)")
            st.metric("🔴 Brief Attendance (<30 min)", f"{brief_attendance} ({brief_attendance/len(df)*100:.1f}%)")
    
    with tab3:
        # Extract hour from join time for time analysis
        join_hours = []
        for _, row in df.iterrows():
            join_time = row['Join Time IST']
            if join_time != 'N/A' and 'IST' in join_time:
                try:
                    hour = int(join_time.split(' ')[1].split(':')[0])
                    join_hours.append(hour)
                except:
                    pass
        
        if join_hours:
            hour_counts = pd.Series(join_hours).value_counts().sort_index()
            
            fig_time = px.bar(
                x=hour_counts.index, 
                y=hour_counts.values,
                title="⏰ Join Time Distribution (Hour of Day)",
                labels={'x': 'Hour (24h format)', 'y': 'Number of Participants'},
                color=hour_counts.values,
                color_continuous_scale='Viridis'
            )
            fig_time.update_layout(height=400)
            st.plotly_chart(fig_time, width='stretch')
        else:
            st.info("No valid join time data available for analysis")
    
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
        file_name=f"zoom_attendance_analytics.csv",
        mime="text/csv"
    )

else:
    st.info("👆 Upload your .env file and select analytics mode to get started!")
    
    st.subheader("📝 Sample .env format:")
    st.code("""
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_MEETING_ID=your_meeting_id
    """, language="bash")