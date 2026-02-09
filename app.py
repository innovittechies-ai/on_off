import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px

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

def get_account_owner(token):
    """Get the account owner user ID"""
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get("https://api.zoom.us/v2/users", headers=headers, params={'page_size': 1})
    if response.status_code == 200:
        users = response.json().get('users', [])
        if users:
            return users[0].get('id') or users[0].get('email')
    return None

def get_meetings_by_date(token, user_id, target_date):
    """Get all past meetings for a specific date"""
    headers = {'Authorization': f'Bearer {token}'}
    url = f"https://api.zoom.us/v2/report/users/{user_id}/meetings"
    params = {'from': target_date, 'to': target_date, 'page_size': 300}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('meetings', [])
    return []

def get_meeting_participants(token, meeting_id):
    """Get participants for a specific meeting"""
    headers = {'Authorization': f'Bearer {token}'}
    url = f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants"
    all_participants = []
    next_page_token = None
    
    while True:
        params = {'page_size': 300}
        if next_page_token:
            params['next_page_token'] = next_page_token
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            all_participants.extend(data.get('participants', []))
            next_page_token = data.get('next_page_token')
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
    if not utc_time_str:
        return 'N/A'
    try:
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        ist_time = utc_time + timedelta(hours=5, minutes=30)
        return ist_time.strftime('%Y-%m-%d %H:%M:%S IST')
    except:
        return utc_time_str

# Main App
st.title("🎯 Zoom Attendance Tracker")
st.markdown("### Track participant attendance")

with st.sidebar:
    st.header("📋 Configuration")
    
    uploaded_file = st.file_uploader("Upload .env file", type=['env'])
    
    if uploaded_file:
        env_vars = parse_env_file(uploaded_file)
        st.success("✅ Environment file loaded!")
        
        mode = st.radio("Select Mode:", ["Find Meeting IDs", "Get Attendance Report"])
        
        if mode == "Find Meeting IDs":
            target_date = st.date_input("Select Date", value=datetime.now() - timedelta(days=1))
            
            if st.button("🔍 Find Meeting IDs", type="primary"):
                with st.spinner("Searching for meetings..."):
                    token = get_zoom_token(
                        env_vars.get('ZOOM_ACCOUNT_ID'),
                        env_vars.get('ZOOM_CLIENT_ID'),
                        env_vars.get('ZOOM_CLIENT_SECRET')
                    )
                    
                    if token:
                        user_id = get_account_owner(token)
                        if not user_id:
                            user_id = "innovit.techies@gmail.com"  # Fallback
                        
                        meetings = get_meetings_by_date(token, user_id, target_date.strftime('%Y-%m-%d'))
                        
                        if meetings:
                            st.success(f"✅ Found {len(meetings)} meetings on {target_date}")
                            st.write("---")
                            for i, meeting in enumerate(meetings, 1):
                                st.write(f"**Meeting {i}:**")
                                st.write(f"📋 **ID:** `{meeting.get('id')}`")
                                st.write(f"📝 **Topic:** {meeting.get('topic', 'N/A')}")
                                st.write(f"⏰ **Start:** {convert_to_ist(meeting.get('start_time', ''))}")
                                st.write(f"⏱️ **Duration:** {meeting.get('duration', 0)} min")
                                st.write("---")
                        else:
                            st.error(f"❌ No meetings found for {target_date}")
                    else:
                        st.error("❌ Authentication failed")
        
        else:  # Get Attendance Report
            meeting_id = st.text_input("Meeting ID", value=env_vars.get('ZOOM_MEETING_ID', ''))
            
            if st.button("🚀 Get Attendance Report", type="primary"):
                if meeting_id:
                    with st.spinner("Fetching attendance data..."):
                        token = get_zoom_token(
                            env_vars.get('ZOOM_ACCOUNT_ID'),
                            env_vars.get('ZOOM_CLIENT_ID'),
                            env_vars.get('ZOOM_CLIENT_SECRET')
                        )
                        
                        if token:
                            participants = get_meeting_participants(token, meeting_id)
                            
                            if participants:
                                st.session_state['participants'] = participants
                                st.success(f"✅ Found {len(participants)} participants!")
                            else:
                                st.error("❌ No participants found")
                        else:
                            st.error("❌ Authentication failed")
                else:
                    st.error("❌ Please enter Meeting ID")

if 'participants' in st.session_state:
    participants = st.session_state['participants']
    
    # Remove duplicates
    unique_participants = {}
    for p in participants:
        email = p.get('user_email', 'N/A')
        name = p.get('name', 'Unknown')
        duration = p.get('duration', 0)
        
        key = email if email != 'N/A' and email != '' else name
        
        if key not in unique_participants or duration > unique_participants[key]['duration']:
            unique_participants[key] = {
                'name': name,
                'email': email,
                'join_time': p.get('join_time', ''),
                'leave_time': p.get('leave_time', ''),
                'duration': duration
            }
    
    # Create DataFrame
    data = []
    for key, p in unique_participants.items():
        duration_minutes = p['duration'] // 60
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
    
    # Analytics
    st.subheader("📊 Attendance Analytics")
    
    tab1, tab2, tab3 = st.tabs(["📈 Duration Analysis", "👥 Participation Overview", "⏰ Time Analysis"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            fig_duration = px.bar(
                df.sort_values('Duration (min)', ascending=False).head(20), 
                x='Name', y='Duration (min)',
                title="🏆 Top 20 Participants by Duration",
                color='Duration (min)',
                color_continuous_scale='Blues'
            )
            fig_duration.update_layout(xaxis_tickangle=45, height=400)
            st.plotly_chart(fig_duration, use_container_width=True)
        
        with col2:
            fig_hist = px.histogram(
                df, x='Duration (min)', 
                nbins=10,
                title="📊 Duration Distribution",
                color_discrete_sequence=['#FF6B6B']
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
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
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
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
            st.plotly_chart(fig_time, use_container_width=True)
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
        use_container_width=True,
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
        file_name=f"zoom_attendance.csv",
        mime="text/csv"
    )

else:
    st.info("👆 Upload your .env file to get started!")
    
    st.subheader("📝 How to use:")
    st.write("**1. Find Meeting IDs:** Select a date to see all meetings held that day")
    st.write("**2. Get Attendance Report:** Enter a Meeting ID to see participant details")
    
    st.subheader("📝 Sample .env format:")
    st.code("""
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
    """, language="bash")
