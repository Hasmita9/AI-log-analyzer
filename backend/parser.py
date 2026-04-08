import json
import re
import csv
from io import StringIO

# ---------- NORMALIZE LEVEL ----------
def normalize_level(level):
    if not level:
        return "INFO"
    level = level.lower()
    if "error" in level or "fail" in level:
        return "ERROR"
    elif "warn" in level:
        return "WARN"
    elif "debug" in level:
        return "DEBUG"
    else:
        return "INFO"


# ---------- PLAIN TEXT ----------
def parse_plain(line):
    try:
        parts = line.split(" ", 2)
        timestamp = parts[0] + " " + parts[1]
        level, message = parts[2].split(" ", 1)

        return {
            "timestamp": timestamp,
            "level": normalize_level(level),
            "message": message,
            "service": "app",
            "source_type": "plain"
        }
    except:
        return None


# ---------- JSON / DOCKER ----------
def parse_json_log(line):
    try:
        data = json.loads(line)

        return {
            "timestamp": data.get("timestamp") or data.get("time"),
            "level": normalize_level(data.get("level") or data.get("severity")),
            "message": data.get("message") or data.get("msg") or data.get("log"),
            "service": data.get("service", "docker"),
            "source_type": "json"
        }
    except:
        return None


# ---------- APACHE ----------
def parse_apache(line):
    try:
        match = re.match(r'(\S+) - - \[(.*?)\] "(.*?)" (\d{3})', line)
        if match:
            return {
                "timestamp": match.group(2),
                "level": "INFO",
                "message": f"{match.group(3)} {match.group(4)}",
                "service": "apache",
                "source_type": "apache"
            }
    except:
        return None


# ---------- NGINX ----------
def parse_nginx(line):
    try:
        match = re.match(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[(.*?)\] .*: (.*)', line)
        if match:
            return {
                "timestamp": match.group(1),
                "level": normalize_level(match.group(2)),
                "message": match.group(3),
                "service": "nginx",
                "source_type": "nginx"
            }
    except:
        return None


# ---------- SYSLOG ----------
def parse_syslog(line):
    try:
        match = re.match(r'(\w{3} \d+ \d{2}:\d{2}:\d{2}) (\S+) (\S+): (.*)', line)
        if match:
            return {
                "timestamp": match.group(1),
                "level": "INFO",
                "message": match.group(4),
                "service": match.group(3),
                "source_type": "syslog"
            }
    except:
        return None


# ---------- CSV ----------
def parse_csv(line):
    try:
        reader = csv.DictReader(StringIO(line))
        for row in reader:
            return {
                "timestamp": row.get("timestamp"),
                "level": normalize_level(row.get("level")),
                "message": row.get("message"),
                "service": row.get("service", "csv"),
                "source_type": "csv"
            }
    except:
        return None


# ---------- MAIN PARSER ----------
def parse_line(line):
    parsers = [
        parse_json_log,
        parse_nginx,
        parse_apache,
        parse_syslog,
        parse_csv,
        parse_plain
    ]

    for parser in parsers:
        result = parser(line)
        if result:
            return result

    return None