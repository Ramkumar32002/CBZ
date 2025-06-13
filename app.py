from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app) # Enable CORS for all routes (already good!)

# Define the path to your SQLite database file
DATABASE = 'database.db'

# --- Database Initialization ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            batting_style TEXT,
            bowling_style TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            did_bat BOOLEAN DEFAULT 0,
            runs INTEGER DEFAULT 0,
            balls INTEGER DEFAULT 0,
            wickets INTEGER DEFAULT 0,
            overs REAL DEFAULT 0.0,
            conceded INTEGER DEFAULT 0,
            catches INTEGER DEFAULT 0,
            stumpings INTEGER DEFAULT 0,
            run_outs INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

# Helper function to get a database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This allows us to access columns by name
    return conn

# Initialize the database when the app starts
# This block ensures init_db is called only when Flask app context is available
with app.app_context():
    init_db()

# --- API Endpoints ---

# Players Endpoints
@app.route('/players', methods=['POST'])
def add_player():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({"error": "Player name is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO players (name, role, batting_style, bowling_style) VALUES (?, ?, ?, ?)",
                       (name, data.get('role'), data.get('batting_style'), data.get('bowling_style')))
        conn.commit()
        player_id = cursor.lastrowid
        new_player = get_db_connection().execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        return jsonify(dict(new_player)), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/players', methods=['GET'])
def get_players():
    conn = get_db_connection()
    players_data = conn.execute("SELECT * FROM players").fetchall()
    players_list = []
    for player_row in players_data:
        player = dict(player_row)
        # Fetch matches for each player
        matches_data = conn.execute("SELECT * FROM matches WHERE player_id = ?", (player['id'],)).fetchall()
        player['matches'] = [dict(match_row) for match_row in matches_data]
        players_list.append(player)
    conn.close()
    return jsonify(players_list)

@app.route('/players/<int:player_id>', methods=['GET'])
def get_player(player_id):
    conn = get_db_connection()
    player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    if player is None:
        conn.close()
        return jsonify({"message": "Player not found"}), 404

    player_dict = dict(player)
    matches_data = conn.execute("SELECT * FROM matches WHERE player_id = ?", (player_id,)).fetchall()
    player_dict['matches'] = [dict(match_row) for match_row in matches_data]
    conn.close()
    return jsonify(player_dict)

@app.route('/players/<int:player_id>', methods=['PUT'])
def update_player(player_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE players SET name=?, role=?, batting_style=?, bowling_style=? WHERE id=?",
                       (data.get('name'), data.get('role'), data.get('batting_style'), data.get('bowling_style'), player_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"message": "Player not found"}), 404
        updated_player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        return jsonify(dict(updated_player))
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/players/<int:player_id>', methods=['DELETE'])
def delete_player(player_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM players WHERE id = ?", (player_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"message": "Player not found"}), 404
        return jsonify({"message": "Player deleted successfully"}), 204 # 204 No Content
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# Matches Endpoints (nested under players for better organization)
@app.route('/players/<int:player_id>/matches', methods=['POST'])
def add_match_for_player(player_id):
    conn = get_db_connection()
    # Check if player exists
    player = conn.execute("SELECT id FROM players WHERE id = ?", (player_id,)).fetchone()
    if player is None:
        conn.close()
        return jsonify({"message": "Player not found"}), 404

    data = request.json
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO matches (player_id, did_bat, runs, balls, wickets, overs, conceded, catches, stumpings, run_outs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (player_id, data.get('did_bat', False), data.get('runs', 0), data.get('balls', 0),
             data.get('wickets', 0), data.get('overs', 0.0), data.get('conceded', 0),
             data.get('catches', 0), data.get('stumpings', 0), data.get('run_outs', 0))
        )
        conn.commit()
        match_id = cursor.lastrowid
        new_match = get_db_connection().execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        return jsonify(dict(new_match)), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/matches/<int:match_id>', methods=['PUT'])
def update_match(match_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE matches SET did_bat=?, runs=?, balls=?, wickets=?, overs=?, conceded=?, catches=?, stumpings=?, run_outs=?
               WHERE id=?""",
            (data.get('did_bat'), data.get('runs'), data.get('balls'), data.get('wickets'),
             data.get('overs'), data.get('conceded'), data.get('catches'), data.get('stumpings'),
             data.get('run_outs'), match_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"message": "Match not found"}), 404
        updated_match = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        return jsonify(dict(updated_match))
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/matches/<int:match_id>', methods=['DELETE'])
def delete_match(match_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"message": "Match not found"}), 404
        return jsonify({"message": "Match deleted successfully"}), 204
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# --- Run the Flask App ---
if __name__ == '__main__':
    # This makes your Flask app accessible from other devices on your network
    app.run(host='0.0.0.0', port=5000, debug=True)
