from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime

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

@app.route("/api/projects", methods=["GET"])
def get_projects():
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()

    return jsonify([dict(row) for row in projects])


@app.route("/api/projects", methods=["POST"])
def create_project():
    data = request.json

    api_key = str(uuid.uuid4())

    conn = get_db()
    conn.execute(
        "INSERT INTO projects (name, description, api_key, created_at) VALUES (?, ?, ?, ?)",
        (data["name"], data["description"], api_key, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Project created", "api_key": api_key})


@app.route("/api/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    errors = conn.execute("SELECT * FROM errors WHERE project_id=?", (project_id,)).fetchall()
    conn.close()

    return jsonify({
        "project": dict(project) if project else None,
        "errors": [dict(e) for e in errors]
    })


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Project deleted"})


@app.route("/api/ingest", methods=["POST"])
def ingest_logs():
    api_key = request.headers.get("X-API-Key")

    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE api_key=?", (api_key,)).fetchone()

    if not project:
        return jsonify({"error": "Invalid API key"}), 401

    logs = request.json.get("logs", [])

    for log in logs:
        conn.execute(
            "INSERT INTO logs (project_id, timestamp, level, message, service, source_type) VALUES (?, ?, ?, ?, ?, ?)",
            (project["id"], datetime.now().isoformat(), "INFO", log, "unknown", "raw")
        )

    conn.commit()
    conn.close()

    return jsonify({"message": "Logs received"})


# ---------- START APP ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)