from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime
from parser import parse_line

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"

# ---------- DATABASE SETUP ----------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        api_key TEXT,
        created_at TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        timestamp TEXT,
        level TEXT,
        message TEXT,
        service TEXT,
        source_type TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        message TEXT,
        count INTEGER,
        severity TEXT,
        first_seen TEXT,
        last_seen TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ai_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        summary TEXT,
        root_causes TEXT,
        fixes TEXT,
        created_at TEXT
    )
    ''')

    conn.commit()
    conn.close()

# ---------- API ROUTES ----------


@app.route("/api/ingest", methods=["POST"])
def ingest_logs():
    api_key = request.headers.get("X-API-Key")

    conn = get_db()
    project = conn.execute(
        "SELECT * FROM projects WHERE api_key=?",
        (api_key,)
    ).fetchone()

    if not project:
        return jsonify({"error": "Invalid API key"}), 401

    logs = request.json.get("logs", [])
    count = 0

    for log in logs:
        parsed = parse_line(log)

        if not parsed:
            continue

        conn.execute(
            "INSERT INTO logs (project_id, timestamp, level, message, service, source_type) VALUES (?, ?, ?, ?, ?, ?)",
            (
                project["id"],
                parsed["timestamp"],
                parsed["level"],
                parsed["message"],
                parsed["service"],
                parsed["source_type"]
            )
        )
        count += 1

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Logs received",
        "count": count
    })

# ---------- PROJECT ROUTES ----------

# GET all projects
@app.route('/api/projects', methods=['GET'])
def get_projects():
    conn = get_db()
    projects = conn.execute(
        "SELECT id, name, description, api_key, created_at FROM projects"
    ).fetchall()

    result = []
    for p in projects:
        result.append({
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "api_key": p["api_key"],
            "created_at": p["created_at"]
        })

    conn.close()
    return jsonify(result)


# CREATE project
@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    name = data.get('name')
    description = data.get('description')

    api_key = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO projects (name, description, api_key, created_at) VALUES (?, ?, ?, ?)",
        (name, description, api_key, created_at)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Project created",
        "api_key": api_key
    })


# GET single project with logs
@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    conn = get_db()

    project = conn.execute(
        "SELECT id, name, description, created_at FROM projects WHERE id=?",
        (project_id,)
    ).fetchone()

    if not project:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    logs = conn.execute(
        "SELECT id, timestamp, level, message FROM logs WHERE project_id=?",
        (project_id,)
    ).fetchall()

    conn.close()

    return jsonify({
        "id": project["id"],
        "name": project["name"],
        "description": project["description"],
        "created_at": project["created_at"],
        "logs": [
            {
                "id": l["id"],
                "timestamp": l["timestamp"],
                "level": l["level"],
                "message": l["message"]
            } for l in logs
        ]
    })


# DELETE project
@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM projects WHERE id=?",
        (project_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Project deleted"})

# ---------- START APP ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)