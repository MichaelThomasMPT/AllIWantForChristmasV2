from flask import Flask, request, jsonify, render_template, send_file
from datetime import datetime, timezone
from pathlib import Path
import csv
import os

app = Flask(__name__)

# Directory where logs are stored
LOG_DIR = Path("data")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# CSV file inside that directory
LOG_FILE = LOG_DIR / "christmas_listens.csv"

def append_log_row(data):
    file_exists = LOG_FILE.exists()

    server_ts = datetime.now(timezone.utc).isoformat()
    client_ts = data.get("client_timestamp", "")
    lat = data.get("latitude")
    lon = data.get("longitude")
    acc = data.get("accuracy")
    ua = request.headers.get("User-Agent", "")

    row = [
        server_ts,
        client_ts,
        f"{lat:.6f}" if isinstance(lat, (int, float)) else "",
        f"{lon:.6f}" if isinstance(lon, (int, float)) else "",
        f"{acc:.2f}" if isinstance(acc, (int, float)) else "",
        ua,
    ]

    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "server_timestamp_utc",
                "client_timestamp",
                "latitude",
                "longitude",
                "accuracy_m",
                "user_agent",
            ])
        writer.writerow(row)


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

    # LOG_FILE should be something like Path("/data/christmas_listens.csv")
    # or Path("christmas_listens.csv") depending on how you configured it.
    try:
        if LOG_FILE.is_file():
            with LOG_FILE.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        elif LOG_FILE.exists() and LOG_FILE.is_dir():
            # Misconfiguration: the path is a directory, not a file
            return (
                "LOG_FILE path points to a directory, not a CSV file. "
                "Check your volume mapping / data directory.",
                500,
            )
        # If it doesn't exist at all, we just show an empty table.
    except Exception as e:
        # Optional: log the error server-side
        app.logger.exception("Error reading log file: %s", e)
        # But still return *something* valid to the browser
        return (
            f"Error reading log file: {e}",
            500,
        )

    # Newest first
    rows = list(reversed(rows))

    return render_template("logs.html", rows=rows)

@app.route("/download", methods=["GET"])
def download_csv():
    if not LOG_FILE.exists():
        # Optionally create an empty file with just headers instead of a junk row:
        with LOG_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "server_timestamp_utc",
                    "client_timestamp",
                    "latitude",
                    "longitude",
                    "accuracy_m",
                    "user_agent",
                ]
            )

    return send_file(
        LOG_FILE,
        mimetype="text/csv",
        as_attachment=True,
        download_name=os.path.basename(LOG_FILE),
    )



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2025, debug=True)
