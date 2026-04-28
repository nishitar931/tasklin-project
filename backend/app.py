from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import sqlite3
import os

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hackathons.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     username TEXT UNIQUE, 
                     password TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS hackathons 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     title TEXT, link TEXT, location TEXT, date TEXT,
                     mode TEXT DEFAULT 'Online',
                     min_team INTEGER DEFAULT 1,
                     max_team INTEGER DEFAULT 4,
                     description TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS waiting_room
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     hackathon_id INTEGER,
                     username TEXT,
                     joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     UNIQUE(hackathon_id, username))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS teams
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     hackathon_id INTEGER,
                     team_name TEXT,
                     members TEXT,
                     formed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

setup_database()

# --- AUTH ROUTES ---

@app.route('/api/signup', methods=['POST'])
def register_user():
    data = request.json
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                     (data['username'], data['password']))
        conn.commit()
        conn.close()
        return jsonify({"result": "success"}), 201
    except:
        return jsonify({"result": "error", "message": "User exists"}), 400

@app.route('/api/login', methods=['POST'])
def authenticate_user():
    data = request.json
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                        (data['username'], data['password'])).fetchone()
    conn.close()
    if user:
        return jsonify({"result": "success", "user": user['username']}), 200
    return jsonify({"result": "failed"}), 401

# --- HACKATHON ROUTES ---

@app.route('/api/hackathons', methods=['GET'])
def fetch_stored_hackathons():
    mode = request.args.get('mode', None)
    conn = get_db_connection()
    if mode and mode != 'All':
        data = conn.execute('SELECT * FROM hackathons WHERE mode = ?', (mode,)).fetchall()
    else:
        data = conn.execute('SELECT * FROM hackathons').fetchall()
    conn.close()
    return jsonify([dict(row) for row in data])

# --- WAITING ROOM ROUTES ---

@app.route('/api/waiting_room/join', methods=['POST'])
def join_waiting_room():
    data = request.json
    hackathon_id = data['hackathon_id']
    username = data['username']
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO waiting_room (hackathon_id, username) VALUES (?, ?)',
                     (hackathon_id, username))
        conn.commit()

        # Check if we can form a team
        hackathon = conn.execute('SELECT * FROM hackathons WHERE id = ?', (hackathon_id,)).fetchone()
        waiting = conn.execute('SELECT * FROM waiting_room WHERE hackathon_id = ?', (hackathon_id,)).fetchall()
        
        count = len(waiting)
        min_team = hackathon['min_team']
        max_team = hackathon['max_team']

        # Auto team formation
        while len(waiting) >= min_team:
            team_members = waiting[:max_team]
            member_names = [m['username'] for m in team_members]
            team_name = f"Team-{hackathon_id}-{len(member_names)}-{team_members[0]['username']}"

            conn.execute('INSERT INTO teams (hackathon_id, team_name, members) VALUES (?, ?, ?)',
                         (hackathon_id, team_name, ','.join(member_names)))

            for member in team_members:
                conn.execute('DELETE FROM waiting_room WHERE hackathon_id = ? AND username = ?',
                             (hackathon_id, member['username']))

            conn.commit()

            # Notify via WebSocket
            socketio.emit('team_formed', {
                'hackathon_id': hackathon_id,
                'team_name': team_name,
                'members': member_names
            }, room=f"hackathon_{hackathon_id}")

            waiting = conn.execute('SELECT * FROM waiting_room WHERE hackathon_id = ?', (hackathon_id,)).fetchall()

        # Broadcast updated waiting count
        new_count = len(conn.execute('SELECT * FROM waiting_room WHERE hackathon_id = ?', (hackathon_id,)).fetchall())
        socketio.emit('waiting_count_update', {
            'hackathon_id': hackathon_id,
            'count': new_count
        }, room=f"hackathon_{hackathon_id}")

        conn.close()
        return jsonify({"result": "success", "waiting_count": new_count}), 200
    except Exception as e:
        return jsonify({"result": "error", "message": str(e)}), 400

@app.route('/api/waiting_room/leave', methods=['POST'])
def leave_waiting_room():
    data = request.json
    hackathon_id = data['hackathon_id']
    username = data['username']
    conn = get_db_connection()
    conn.execute('DELETE FROM waiting_room WHERE hackathon_id = ? AND username = ?',
                 (hackathon_id, username))
    conn.commit()
    count = len(conn.execute('SELECT * FROM waiting_room WHERE hackathon_id = ?', (hackathon_id,)).fetchall())
    conn.close()

    socketio.emit('waiting_count_update', {
        'hackathon_id': hackathon_id,
        'count': count
    }, room=f"hackathon_{hackathon_id}")

    return jsonify({"result": "success", "waiting_count": count}), 200

@app.route('/api/waiting_room/count/<int:hackathon_id>', methods=['GET'])
def get_waiting_count(hackathon_id):
    conn = get_db_connection()
    count = len(conn.execute('SELECT * FROM waiting_room WHERE hackathon_id = ?', (hackathon_id,)).fetchall())
    conn.close()
    return jsonify({"count": count})

@app.route('/api/waiting_room/status', methods=['GET'])
def get_user_waiting_status():
    username = request.args.get('username')
    hackathon_id = request.args.get('hackathon_id')
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM waiting_room WHERE hackathon_id = ? AND username = ?',
                       (hackathon_id, username)).fetchone()
    conn.close()
    return jsonify({"in_waiting_room": row is not None})

@app.route('/api/teams/<int:hackathon_id>', methods=['GET'])
def get_teams(hackathon_id):
    conn = get_db_connection()
    teams = conn.execute('SELECT * FROM teams WHERE hackathon_id = ?', (hackathon_id,)).fetchall()
    conn.close()
    return jsonify([dict(t) for t in teams])

# --- WEBSOCKET EVENTS ---

@socketio.on('subscribe')
def handle_subscribe(data):
    hackathon_id = data.get('hackathon_id')
    join_room(f"hackathon_{hackathon_id}")

if __name__ == '__main__':
    print("🚀 BACKEND STARTING ON PORT 8000...")
    socketio.run(app, debug=True, port=8000)