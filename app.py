from flask import Flask, request, jsonify, render_template, send_file
from datetime import datetime, timezone
from zoneinfo import ZoneInfo 
import os
from pathlib import Path
import csv
import requests

app = Flask(__name__)

# Directory where logs are stored
LOG_DIR = Path("data")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# CSV file inside that directory
LOG_FILE = LOG_DIR / "christmas_listens.csv"

# User timezone for displaying log times
USER_TIMEZONE = os.getenv("USER_TIMEZONE", "UTC")
USER_TZ = ZoneInfo(USER_TIMEZONE)

def append_log_row(data):
    file_exists = LOG_FILE.exists()

    server_ts = datetime.now(timezone.utc).isoformat()
    client_ts = data.get("client_timestamp", "")
    lat = data.get("latitude")
    lon = data.get("longitude")

    # Convert to numeric if possible
    lat_val = lat if isinstance(lat, (int, float)) else None
    lon_val = lon if isinstance(lon, (int, float)) else None

    # Reverse geocode if we have coordinates
    location_name = ""
    if lat_val is not None and lon_val is not None:
        location_name = reverse_geocode(lat_val, lon_val)

    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header only if file doesn't exist yet
        if not file_exists:
            writer.writerow([
                "server_timestamp_utc",
                "client_timestamp",
                "latitude",
                "longitude",
                "location_name",
            ])

        writer.writerow([
            server_ts,
            client_ts,
            f"{lat_val:.6f}" if lat_val is not None else "",
            f"{lon_val:.6f}" if lon_val is not None else "",
            location_name,
        ])

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/log", methods=["POST"])
def log_listen():
    try:
        data = request.get_json(force=True) or {}
        append_log_row(data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/logs", methods=["GET"])
def view_logs():
    rows = []
    if LOG_FILE.exists() and LOG_FILE.is_file():
        with LOG_FILE.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    # Convert server_timestamp_utc (ISO, UTC) into user's timezone
    for row in rows:
        raw_ts = row.get("server_timestamp_utc", "")
        display = raw_ts
        try:
            # Handle ISO datetime (with or without tz)
            dt = datetime.fromisoformat(raw_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone(USER_TZ)
            # Human-readable, no timezone suffix
            display = local_dt.strftime("%d %b %Y, %H:%M:%S")
        except Exception:
            # If parsing fails, fall back to raw string
            pass

        row["display_time"] = display
        row["location_name"] = row.get("location_name", "")

    return render_template(
        "logs.html",
        rows=rows,
    )

def reverse_geocode(lat, lon):
    """
    Return a human-readable location string for given lat/lon.
    Uses Nominatim (OpenStreetMap). Keep query rate low.
    """
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 14,
            "addressdetails": 1,
        }

        headers = {
            "User-Agent": "all-i-want-for-christmas/1.0"
        }

        r = requests.get(url, params=params, headers=headers, timeout=4)
        r.raise_for_status()
        data = r.json()

        addr = data.get("address", {})
        parts = [
            addr.get("suburb"),
            addr.get("city") or addr.get("town") or addr.get("village"),
            addr.get("state"),
            addr.get("country")
        ]
        parts = [p for p in parts if p]
        return ", ".join(parts) if parts else data.get("display_name", "")
    except Exception:
        return ""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2025, debug=True)
