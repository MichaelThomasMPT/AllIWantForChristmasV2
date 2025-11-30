from flask import Flask, request, jsonify, render_template, Response
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

# Maximum number of data rows allowed in the CSV
MAX_ROWS = 1000

# User timezone for displaying log times (default UTC)
USER_TIMEZONE = os.getenv("USER_TIMEZONE", "UTC")
USER_TZ = ZoneInfo(USER_TIMEZONE)


def get_row_count() -> int:
    """
    Return the number of data rows currently in the CSV (excluding header).
    If the file doesn't exist, returns 0.
    """
    if not LOG_FILE.exists() or not LOG_FILE.is_file():
        return 0

    count = 0
    with LOG_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        # Skip header if present
        try:
            next(reader)
        except StopIteration:
            return 0

        for _ in reader:
            count += 1

    return count


def append_log_row(lat: float | None, lon: float | None) -> None:
    """
    Append a row to the CSV log using server time (UTC) and optional coordinates.
    Assumes the caller has already checked the row-count limit.
    """
    file_exists = LOG_FILE.exists()
    server_ts = datetime.now(timezone.utc).isoformat()

    # Reverse geocode if we have valid coordinates
    location_name = ""
    if lat is not None and lon is not None:
        location_name = reverse_geocode(lat, lon)

    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # New header (no client_timestamp anymore)
        if not file_exists:
            writer.writerow(
                [
                    "server_timestamp_utc",
                    "latitude",
                    "longitude",
                    "location_name",
                ]
            )

        writer.writerow(
            [
                server_ts,
                f"{lat:.6f}" if lat is not None else "",
                f"{lon:.6f}" if lon is not None else "",
                location_name,
            ]
        )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/log", methods=["POST"])
def log_listen():
    """
    Accepts ONLY:
    {
      "latitude": <number>,
      "longitude": <number>
    }
    - No extra fields allowed
    - Lat in [-90, 90], Lon in [-180, 180]
    - Rejects if CSV already has MAX_ROWS rows.
    """
    # Enforce maximum rows first
    current_rows = get_row_count()
    if current_rows >= MAX_ROWS:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Log is full ({MAX_ROWS} entries). "
                             f"Please archive or delete the file before logging more.",
                }
            ),
            429,
        )

    data = request.get_json(force=True, silent=True)

    if not isinstance(data, dict):
        return (
            jsonify({"success": False, "error": "JSON body must be an object"}),
            400,
        )

    allowed_keys = {"latitude", "longitude"}
    keys = set(data.keys())

    missing = allowed_keys - keys
    extra = keys - allowed_keys

    if missing:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Missing fields: {', '.join(sorted(missing))}",
                }
            ),
            400,
        )

    if extra:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Unexpected fields: {', '.join(sorted(extra))}",
                }
            ),
            400,
        )

    # Validate numeric + range
    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
    except (TypeError, ValueError):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Latitude and longitude must be numbers",
                }
            ),
            400,
        )

    if not (-90.0 <= lat <= 90.0):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Latitude must be between -90 and 90",
                }
            ),
            400,
        )

    if not (-180.0 <= lon <= 180.0):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Longitude must be between -180 and 180",
                }
            ),
            400,
        )

    try:
        append_log_row(lat, lon)
        return jsonify({"success": True})
    except Exception:
        # You can log the exception here if you want
        return jsonify({"success": False, "error": "Internal error"}), 500


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
            dt = datetime.fromisoformat(raw_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone(USER_TZ)
            # Human-readable, no timezone suffix
            display = local_dt.strftime("%d %b %Y, %H:%M:%S")
        except Exception:
            pass

        row["display_time"] = display
        row["location_name"] = row.get("location_name", "")

    return render_template("logs.html", rows=rows)


@app.route("/robots.txt")
def robots_txt():
    """
    Tell well-behaved crawlers not to index the logs.
    (Doesn't provide real security, but avoids accidental exposure.)
    """
    content = "User-agent: *\nDisallow: /logs\n"
    return Response(content, mimetype="text/plain")


def reverse_geocode(lat: float, lon: float) -> str:
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

        headers = {"User-Agent": "all-i-want-for-christmas/1.0"}

        r = requests.get(url, params=params, headers=headers, timeout=4)
        r.raise_for_status()
        data = r.json()

        addr = data.get("address", {})
        parts = [
            addr.get("suburb"),
            addr.get("city") or addr.get("town") or addr.get("village"),
            addr.get("state"),
            addr.get("country"),
        ]
        parts = [p for p in parts if p]
        return ", ".join(parts) if parts else data.get("display_name", "")
    except Exception:
        return ""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2025, debug=True)
