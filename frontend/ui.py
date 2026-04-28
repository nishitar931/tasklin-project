import streamlit as st
import requests
import time

st.set_page_config(page_title="HackTracker 2026", page_icon="🚀", layout="wide")

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'page' not in st.session_state:
    st.session_state['page'] = 'home'
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'selected_mode' not in st.session_state:
    st.session_state['selected_mode'] = 'All'
if 'notifications' not in st.session_state:
    st.session_state['notifications'] = []
if 'waiting_rooms' not in st.session_state:
    st.session_state['waiting_rooms'] = {}  # {hackathon_id: True/False}

API_URL = "http://127.0.0.1:8000/api"

# --- CUSTOM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }

    .hack-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }

    .hack-card:hover {
        border-color: #e94560;
        box-shadow: 0 0 20px rgba(233, 69, 96, 0.2);
    }

    .mode-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .badge-online {
        background: rgba(0, 255, 136, 0.15);
        color: #00ff88;
        border: 1px solid #00ff88;
    }

    .badge-offline {
        background: rgba(255, 165, 0, 0.15);
        color: #ffa500;
        border: 1px solid #ffa500;
    }

    .badge-hybrid {
        background: rgba(100, 149, 237, 0.15);
        color: #6495ed;
        border: 1px solid #6495ed;
    }

    .waiting-box {
        background: rgba(233, 69, 96, 0.08);
        border: 1px solid rgba(233, 69, 96, 0.3);
        border-radius: 12px;
        padding: 12px 16px;
        margin-top: 10px;
    }

    .notification-box {
        background: rgba(0, 255, 136, 0.1);
        border-left: 4px solid #00ff88;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 8px;
    }

    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #888;
    }

    .filter-bar {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 24px;
    }
</style>
""", unsafe_allow_html=True)


# --- HEADER ---
def render_header():
    col_l, col_m, col_r = st.columns([1, 4, 1.5])

    with col_l:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()

    with col_r:
        if not st.session_state['logged_in']:
            if st.button("🔑 Login / Signup", use_container_width=True):
                st.session_state['page'] = 'login'
                st.rerun()
        else:
            u_col, out_col = st.columns([2, 1])
            u_col.write(f"👤 **{st.session_state['username']}**")
            if out_col.button("Logout"):
                st.session_state['logged_in'] = False
                st.session_state['username'] = ""
                st.session_state['page'] = 'home'
                st.session_state['waiting_rooms'] = {}
                st.rerun()

    # --- NOTIFICATIONS ---
    if st.session_state['notifications']:
        st.markdown("### 🔔 Notifications")
        for notif in st.session_state['notifications']:
            st.markdown(f"""
            <div class="notification-box">
                ✅ {notif}
            </div>
            """, unsafe_allow_html=True)
        if st.button("Clear Notifications"):
            st.session_state['notifications'] = []
            st.rerun()

    st.divider()


# --- MODE FILTER BAR ---
def render_filter_bar():
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown("**🎛️ Filter Mode:**")
    with col2:
        mode = st.radio(
            label="mode_filter",
            options=["All", "Online", "Offline", "Hybrid"],
            horizontal=True,
            label_visibility="collapsed",
            index=["All", "Online", "Offline", "Hybrid"].index(st.session_state['selected_mode'])
        )
        if mode != st.session_state['selected_mode']:
            st.session_state['selected_mode'] = mode
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# --- WAITING ROOM HELPERS ---
def get_waiting_count(hackathon_id):
    try:
        res = requests.get(f"{API_URL}/waiting_room/count/{hackathon_id}")
        return res.json().get("count", 0)
    except:
        return 0

def check_user_in_waiting_room(hackathon_id, username):
    try:
        res = requests.get(f"{API_URL}/waiting_room/status",
                           params={"hackathon_id": hackathon_id, "username": username})
        return res.json().get("in_waiting_room", False)
    except:
        return False

def join_waiting_room(hackathon_id, username):
    try:
        res = requests.post(f"{API_URL}/waiting_room/join",
                            json={"hackathon_id": hackathon_id, "username": username})
        data = res.json()

        # Check if a team was formed for this user
        teams_res = requests.get(f"{API_URL}/teams/{hackathon_id}")
        teams = teams_res.json()
        for team in teams:
            if username in team['members'].split(','):
                st.session_state['notifications'].append(
                    f"🎉 You've been placed in **{team['team_name']}** for hackathon #{hackathon_id}!"
                )
                st.session_state['waiting_rooms'].pop(hackathon_id, None)
                return

        st.session_state['waiting_rooms'][hackathon_id] = True
        return data.get('waiting_count', 0)
    except Exception as e:
        st.error(f"Error joining waiting room: {e}")

def leave_waiting_room(hackathon_id, username):
    try:
        requests.post(f"{API_URL}/waiting_room/leave",
                      json={"hackathon_id": hackathon_id, "username": username})
        st.session_state['waiting_rooms'].pop(hackathon_id, None)
    except:
        pass


# --- HOME PAGE ---
def show_home():
    st.title("🚀 Upcoming Hackathons 2026")
    render_filter_bar()

    try:
        mode_param = st.session_state['selected_mode']
        res = requests.get(f"{API_URL}/hackathons", params={"mode": mode_param})
        hackathons = res.json()

        if not hackathons:
            st.markdown(f"""
            <div class="empty-state">
                <h2>😕</h2>
                <h3>No {mode_param} hackathons available right now.</h3>
                <p>Try a different mode or check back later!</p>
            </div>
            """, unsafe_allow_html=True)
            return

        st.markdown(f"**{len(hackathons)} hackathon(s) found**")

        for h in hackathons:
            hackathon_id = h['id']
            mode = h.get('mode', 'Online')
            badge_class = f"badge-{mode.lower()}"

            waiting_count = get_waiting_count(hackathon_id)

            # Check if current user is in waiting room
            in_waiting = False
            if st.session_state['logged_in']:
                in_waiting = check_user_in_waiting_room(hackathon_id, st.session_state['username'])
                st.session_state['waiting_rooms'][hackathon_id] = in_waiting

            st.markdown(f"""
            <div class="hack-card">
                <span class="mode-badge {badge_class}">{mode}</span>
                <h3 style="margin:4px 0; color:#fff;">{h['title']}</h3>
                <p style="color:#aaa; font-size:13px; margin:4px 0;">
                    📅 {h.get('date', 'TBA')} &nbsp;|&nbsp; 📍 {h.get('location', 'India')}
                </p>
                <p style="color:#ccc; font-size:13px;">{h.get('description', '')}</p>
                <p style="color:#888; font-size:12px;">
                    👥 Team size: {h.get('min_team', 1)}–{h.get('max_team', 4)} members
                </p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns([2, 2, 2])

            with col1:
                st.link_button("🔗 View Details", h['link'])

            with col2:
                st.markdown(f"""
                <div class="waiting-box">
                    ⏳ <b>{waiting_count}</b> people waiting for teammates
                </div>
                """, unsafe_allow_html=True)

            with col3:
                if st.session_state['logged_in']:
                    if in_waiting:
                        if st.button(f"🚪 Leave Waiting Room", key=f"leave_{hackathon_id}"):
                            leave_waiting_room(hackathon_id, st.session_state['username'])
                            st.success("You've left the waiting room.")
                            time.sleep(1)
                            st.rerun()
                    else:
                        if st.button(f"🤝 Join Waiting Room", key=f"join_{hackathon_id}"):
                            count = join_waiting_room(hackathon_id, st.session_state['username'])
                            if st.session_state['notifications']:
                                st.rerun()
                            else:
                                st.success(f"✅ Joined! {count} people now waiting.")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.info("🔑 Login to join waiting room")

            st.write("")

    except Exception as e:
        st.error(f"Could not connect to backend. Is app.py running? ({e})")


# --- LOGIN PAGE ---
def show_login():
    st.header("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login Now", use_container_width=True):
        try:
            res = requests.post(f"{API_URL}/login",
                                json={"username": username, "password": password})
            if res.status_code == 200:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['page'] = 'home'
                st.rerun()
            else:
                st.error("Invalid credentials.")
        except:
            st.error("Backend offline.")

    st.write("---")
    st.write("Don't have an account?")
    if st.button("Create a New Account (Sign Up)"):
        st.session_state['page'] = 'signup'
        st.rerun()


# --- SIGNUP PAGE ---
def show_signup():
    st.header("📝 Sign Up")
    new_user = st.text_input("Choose Username")
    new_pwd = st.text_input("Choose Password", type="password")

    if st.button("Register Account", use_container_width=True):
        try:
            res = requests.post(f"{API_URL}/signup",
                                json={"username": new_user, "password": new_pwd})
            if res.status_code == 201:
                st.success("Account created! Go to Login.")
            else:
                st.error("Username already taken.")
        except:
            st.error("Backend offline.")

    if st.button("← Back to Login"):
        st.session_state['page'] = 'login'
        st.rerun()


# --- ROUTING ---
render_header()

if st.session_state['page'] == 'login':
    show_login()
elif st.session_state['page'] == 'signup':
    show_signup()
else:
    show_home()
