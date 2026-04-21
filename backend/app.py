from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime
from parser import parse_line
import re
import os
from dotenv import load_dotenv
from google import genai
import requests as http_requests
from flask import send_from_directory
import os

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


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

    print("Project fetched:", project)

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

    # detects the errors in the logs
    detect_errors(project["id"])
    generate_ai_summary(project["id"]) # generates the ai summary

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


# DETECT ERRORS function
def detect_errors(project_id):
    conn = get_db()

    logs = conn.execute(
        "SELECT message, timestamp, level FROM logs WHERE project_id=? AND (level='ERROR' OR level='WARN')",
        (project_id,)
    ).fetchall()

    error_map = {}

    def normalize(msg):
        msg = msg.lower()
        msg = re.sub(r'\d+', '', msg)
        return msg.strip()

    for log in logs:
        normalized = normalize(log["message"])

        if normalized not in error_map:
            error_map[normalized] = {
                "message": log["message"],
                "count": 0,
                "first_seen": log["timestamp"],
                "last_seen": log["timestamp"]
            }

        error_map[normalized]["count"] += 1

        if log["timestamp"] < error_map[normalized]["first_seen"]:
            error_map[normalized]["first_seen"] = log["timestamp"]

        if log["timestamp"] > error_map[normalized]["last_seen"]:
            error_map[normalized]["last_seen"] = log["timestamp"]

    def classify(msg):
        m = msg.lower()
        if any(x in m for x in ["crash", "fatal", "killed", "segfault", "panic"]):
            return "Critical"
        elif any(x in m for x in ["error", "failed", "exception", "refused", "unavailable"]):
            return "High"
        elif any(x in m for x in ["warn", "warning", "timeout", "slow", "retry"]):
            return "Medium"
        else:
            return "Low"

    for err in error_map.values():
        severity = classify(err["message"])

        existing = conn.execute(
            "SELECT id FROM errors WHERE project_id=? AND message=?",
            (project_id, err["message"])
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE errors SET count=?, severity=?, last_seen=?
                WHERE project_id=? AND message=?
                """,
                (err["count"], severity, err["last_seen"], project_id, err["message"])
            )
        else:
            conn.execute(
                """
                INSERT INTO errors (project_id, message, count, severity, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, err["message"], err["count"], severity, err["first_seen"], err["last_seen"])
            )

    conn.commit()
    conn.close()


# GET errors for a project
@app.route('/api/projects/<int:project_id>/errors', methods=['GET'])
def get_project_errors(project_id):
    conn = get_db()

    errors = conn.execute(
        """
        SELECT id, message, count, severity, first_seen, last_seen
        FROM errors
        WHERE project_id=?
        ORDER BY count DESC
        """,
        (project_id,)
    ).fetchall()

    conn.close()

    return jsonify([
        {
            "id": e["id"],
            "message": e["message"],
            "count": e["count"],
            "severity": e["severity"],
            "first_seen": e["first_seen"],
            "last_seen": e["last_seen"]
        } for e in errors
    ])

# GENERATE AI SUMMARY function
def generate_ai_summary(project_id):
    print("👉 generate_ai_summary called for project:", project_id)

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY is missing")
        return
    else:
        print("✅ GEMINI_API_KEY found")

    conn = get_db()

    critical = conn.execute(
        "SELECT * FROM errors WHERE project_id=? AND severity='Critical'",
        (project_id,)
    ).fetchall()

    high = conn.execute(
        "SELECT * FROM errors WHERE project_id=? AND severity='High' ORDER BY count DESC LIMIT 5",
        (project_id,)
    ).fetchall()

    medium = conn.execute(
        "SELECT * FROM errors WHERE project_id=? AND severity='Medium' ORDER BY count DESC LIMIT 3",
        (project_id,)
    ).fetchall()

    selected_errors = list(critical) + list(high) + list(medium)
    selected_errors = selected_errors[:20]

    if not selected_errors:
        conn.close()
        return

    error_text = "\n".join([
        f"{e['message']} (count={e['count']}, severity={e['severity']})"
        for e in selected_errors
    ])

    prompt = f"""
    Analyze the following application errors:

    {error_text}

    Provide:
    - Summary in simple English
    - Root causes (bullet points)
    - Recommended fixes (bullet points)
    """

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        response = http_requests.post(url, json=body)
        result = response.json()
        print("FULL API RESPONSE:", result)

        if "candidates" in result:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print("Full API response:", result)
            text = "AI summary unavailable (quota issue)"
        print("AI response generated, saving to DB...")

        conn.execute(
            """
            INSERT INTO ai_insights (project_id, summary, root_causes, fixes, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                project_id,
                text,
                text,
                text,
                datetime.utcnow().isoformat()
            )
        )

        conn.commit()

    except Exception as e:
        print("AI Error:", e)

    conn.close()

# GET latest AI insight for a project
@app.route('/api/projects/<int:project_id>/insights', methods=['GET'])
def get_project_insights(project_id):
    conn = get_db()

    insight = conn.execute(
        """
        SELECT summary, root_causes, fixes, created_at
        FROM ai_insights
        WHERE project_id=?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,)
    ).fetchone()

    conn.close()

    if not insight:
        return jsonify({"message": "No insights found"})

    return jsonify({
        "summary": insight["summary"],
        "root_causes": insight["root_causes"],
        "fixes": insight["fixes"],
        "created_at": insight["created_at"]
    })

# GENERATE AI INSIGHT ON DEMAND
@app.route('/api/projects/<int:project_id>/insights/generate', methods=['POST'])
def generate_insight_on_demand(project_id):
    conn = get_db()
    project = conn.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone()
    conn.close()

    if not project:
        return jsonify({"error": "Project not found"}), 404

    # 🔥 This calls Gemini AI (your existing function)
    generate_ai_summary(project_id)

    # Fetch latest generated insight
    conn = get_db()
    insight = conn.execute(
        """
        SELECT summary, root_causes, fixes, created_at
        FROM ai_insights
        WHERE project_id=?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,)
    ).fetchone()
    conn.close()

    if not insight:
        return jsonify({"error": "Could not generate insight"}), 500

    return jsonify({
        "summary": insight["summary"],
        "root_causes": insight["root_causes"],
        "fixes": insight["fixes"],
        "created_at": insight["created_at"]
    })
# SERVE FRONTEND
@app.route("/")
def serve_frontend():
    return send_from_directory("../frontend", "index.html")

# SERVE STATIC FILES
@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("../frontend", path)

# ---------- START APP ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)