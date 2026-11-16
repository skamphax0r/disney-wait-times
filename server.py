#!/usr/bin/env python3
"""
Disney Wait Times Display Box Server
Serves a retro Disney wait times smart-clock display box web app.
Pulls live wait times from queue-times.com with caching.
"""

import http.server
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

PORT = int(os.environ.get("PORT", 8088))
CACHE_TTL = 60  # Cache wait times for 60 seconds

PARKS = [
    {
        "id": 6,
        "name": "Magic Kingdom",
        "resort": "Walt Disney World",
        "timezone": "America/New_York",
        "theme_color": "#2563eb",
        "accent_color": "#fbbf24",
        "icon": "🏰",
    },
    {
        "id": 5,
        "name": "EPCOT",
        "resort": "Walt Disney World",
        "timezone": "America/New_York",
        "theme_color": "#7c3aed",
        "accent_color": "#38bdf8",
        "icon": "🌐",
    },
    {
        "id": 7,
        "name": "Disney's Hollywood Studios",
        "resort": "Walt Disney World",
        "timezone": "America/New_York",
        "theme_color": "#dc2626",
        "accent_color": "#facc15",
        "icon": "🎬",
    },
    {
        "id": 8,
        "name": "Disney's Animal Kingdom",
        "resort": "Walt Disney World",
        "timezone": "America/New_York",
        "theme_color": "#059669",
        "accent_color": "#a3e635",
        "icon": "🦁",
    },
    {
        "id": 16,
        "name": "Disneyland Park",
        "resort": "Disneyland Resort",
        "timezone": "America/Los_Angeles",
        "theme_color": "#1d4ed8",
        "accent_color": "#f59e0b",
        "icon": "✨",
    },
    {
        "id": 17,
        "name": "Disney California Adventure",
        "resort": "Disneyland Resort",
        "timezone": "America/Los_Angeles",
        "theme_color": "#b91c1c",
        "accent_color": "#fbbf24",
        "icon": "🎡",
    },
    {
        "id": 4,
        "name": "Disneyland Paris",
        "resort": "Disneyland Paris",
        "timezone": "Europe/Paris",
        "theme_color": "#4338ca",
        "accent_color": "#f472b6",
        "icon": "👑",
    },
    {
        "id": 274,
        "name": "Tokyo Disneyland",
        "resort": "Tokyo Disney Resort",
        "timezone": "Asia/Tokyo",
        "theme_color": "#0284c7",
        "accent_color": "#fb923c",
        "icon": "🗻",
    },
    {
        "id": 275,
        "name": "Tokyo DisneySea",
        "resort": "Tokyo Disney Resort",
        "timezone": "Asia/Tokyo",
        "theme_color": "#0d9488",
        "accent_color": "#38bdf8",
        "icon": "🌋",
    },
]

# In-memory cache: { park_id: (timestamp, data) }
cache: Dict[int, tuple] = {}


def fetch_park_data(park_id: int) -> Dict[str, Any]:
    now = time.time()
    if park_id in cache:
        cached_time, cached_data = cache[park_id]
        if now - cached_time < CACHE_TTL:
            return cached_data

    url = f"https://queue-times.com/parks/{park_id}/queue_times.json"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        rides = []
        lands = data.get("lands", [])
        for land in lands:
            land_name = land.get("name", "Attractions")
            for r in land.get("rides", []):
                rides.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "land": land_name,
                    "is_open": bool(r.get("is_open", False)),
                    "wait_time": int(r.get("wait_time") or 0),
                    "last_updated": r.get("last_updated"),
                })

        for r in data.get("rides", []):
            rides.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "land": "Attractions",
                "is_open": bool(r.get("is_open", False)),
                "wait_time": int(r.get("wait_time") or 0),
                "last_updated": r.get("last_updated"),
            })

        # Calculate summary statistics
        open_rides = [r for r in rides if r["is_open"]]
        avg_wait = round(sum(r["wait_time"] for r in open_rides) / len(open_rides)) if open_rides else 0
        max_wait = max((r["wait_time"] for r in open_rides), default=0)

        result = {
            "park_id": park_id,
            "rides": rides,
            "total_rides": len(rides),
            "open_rides": len(open_rides),
            "closed_rides": len(rides) - len(open_rides),
            "avg_wait": avg_wait,
            "max_wait": max_wait,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now)),
        }

        cache[park_id] = (now, result)
        return result

    except Exception as e:
        print(f"Error fetching data for park {park_id}: {e}", file=sys.stderr)
        if park_id in cache:
            # Return stale cache if available
            return cache[park_id][1]
        raise


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        directory = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/parks":
            self.send_json(200, {"parks": PARKS})
            return

        if path.startswith("/api/parks/") and path.endswith("/waits"):
            try:
                parts = path.strip("/").split("/")
                park_id = int(parts[2])
                data = fetch_park_data(park_id)
                self.send_json(200, data)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/health":
            self.send_json(200, {"status": "ok", "time": time.time()})
            return

        # Serve index.html or static assets
        if path == "/":
            self.path = "/index.html"

        return super().do_GET()

    def send_json(self, status_code: int, data: Any):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Keep logs clean
        sys.stdout.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.address_string()} - {format % args}\n")


def run():
    server_address = ("0.0.0.0", PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, RequestHandler)
    print(f"🏰 Disney Wait Times Box Server running on http://0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    run()
