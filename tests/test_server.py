"""
Unit and integration tests for Disney Wait Times Display Box server.
"""

import json
import os
import sys
import threading
import time
import unittest
from http.client import HTTPConnection
from unittest.mock import MagicMock, patch

# Add parent directory to path to import server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import server


class TestParkData(unittest.TestCase):
    """Test park configuration and data integrity."""

    def test_parks_list_non_empty(self):
        self.assertGreater(len(server.PARKS), 0)

    def test_parks_required_keys(self):
        required_keys = {"id", "name", "resort", "timezone", "theme_color", "accent_color", "icon"}
        for park in server.PARKS:
            with self.subTest(park=park["name"]):
                self.assertTrue(required_keys.issubset(park.keys()))
                self.assertIsInstance(park["id"], int)
                self.assertIsInstance(park["name"], str)
                self.assertTrue(len(park["name"]) > 0)


class TestWaitTimeParsingAndCaching(unittest.TestCase):
    """Test wait time data fetching, parsing, and caching logic."""

    def setUp(self):
        # Clear cache before each test
        server.cache.clear()

    @patch("urllib.request.urlopen")
    def test_fetch_park_data_success(self, mock_urlopen):
        mock_response_data = {
            "lands": [
                {
                    "id": 1,
                    "name": "Fantasyland",
                    "rides": [
                        {"id": 101, "name": "Peter Pan's Flight", "is_open": True, "wait_time": 45, "last_updated": "2026-11-16T00:00:00Z"},
                        {"id": 102, "name": "Seven Dwarfs Mine Train", "is_open": True, "wait_time": 65, "last_updated": "2026-11-16T00:00:00Z"},
                        {"id": 103, "name": "It's a Small World", "is_open": False, "wait_time": 0, "last_updated": "2026-11-16T00:00:00Z"}
                    ]
                }
            ],
            "rides": [
                {"id": 201, "name": "Space Mountain", "is_open": True, "wait_time": 40, "last_updated": "2026-11-16T00:00:00Z"}
            ]
        }
        mock_ctx = MagicMock()
        mock_ctx.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_ctx

        result = server.fetch_park_data(6)

        self.assertEqual(result["park_id"], 6)
        self.assertEqual(result["total_rides"], 4)
        self.assertEqual(result["open_rides"], 3)
        self.assertEqual(result["closed_rides"], 1)
        # avg wait of open rides: (45 + 65 + 40) / 3 = 150 / 3 = 50
        self.assertEqual(result["avg_wait"], 50)
        self.assertEqual(result["max_wait"], 65)
        self.assertIn("fetched_at", result)

    @patch("urllib.request.urlopen")
    def test_caching_behavior(self, mock_urlopen):
        mock_response_data = {
            "lands": [],
            "rides": [{"id": 301, "name": "Haunted Mansion", "is_open": True, "wait_time": 25, "last_updated": "2026-11-16T00:00:00Z"}]
        }
        mock_ctx = MagicMock()
        mock_ctx.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_ctx

        # First call hits network
        data1 = server.fetch_park_data(6)
        self.assertEqual(mock_urlopen.call_count, 1)

        # Second call within TTL returns cached data without calling urlopen
        data2 = server.fetch_park_data(6)
        self.assertEqual(mock_urlopen.call_count, 1)
        self.assertEqual(data1, data2)

    @patch("urllib.request.urlopen")
    def test_stale_cache_fallback_on_network_error(self, mock_urlopen):
        # Seed cache with initial valid data
        now = time.time()
        stale_data = {"park_id": 6, "rides": [], "total_rides": 0, "open_rides": 0, "closed_rides": 0, "avg_wait": 0, "max_wait": 0}
        server.cache[6] = (now - 120, stale_data)  # Expired cache entry

        # Upstream throws error
        mock_urlopen.side_effect = Exception("Connection timed out")

        # Function should return stale cache instead of failing completely
        result = server.fetch_park_data(6)
        self.assertEqual(result, stale_data)


class TestServerEndpoints(unittest.TestCase):
    """Integration tests running against RequestHandler."""

    @classmethod
    def setUpClass(cls):
        # Start test HTTP server on an ephemeral free port
        cls.server = server.http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.RequestHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, resp.headers, data

    def test_health_endpoint(self):
        status, headers, data = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "application/json; charset=utf-8")
        body = json.loads(data.decode("utf-8"))
        self.assertEqual(body.get("status"), "ok")
        self.assertIn("time", body)

    def test_parks_endpoint(self):
        status, headers, data = self.get("/api/parks")
        self.assertEqual(status, 200)
        body = json.loads(data.decode("utf-8"))
        self.assertIn("parks", body)
        self.assertIsInstance(body["parks"], list)
        self.assertGreater(len(body["parks"]), 0)

    @patch("server.fetch_park_data")
    def test_park_waits_endpoint(self, mock_fetch):
        mock_fetch.return_value = {
            "park_id": 6,
            "rides": [{"id": 1, "name": "Big Thunder Mountain", "is_open": True, "wait_time": 30}],
            "total_rides": 1,
            "open_rides": 1,
            "closed_rides": 0,
            "avg_wait": 30,
            "max_wait": 30
        }
        status, headers, data = self.get("/api/parks/6/waits")
        self.assertEqual(status, 200)
        body = json.loads(data.decode("utf-8"))
        self.assertEqual(body["park_id"], 6)
        self.assertEqual(body["total_rides"], 1)

    def test_root_serves_index_html(self):
        status, headers, data = self.get("/")
        self.assertEqual(status, 200)
        content = data.decode("utf-8")
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("Disney Wait Times", content)

    def test_static_index_html(self):
        status, headers, data = self.get("/index.html")
        self.assertEqual(status, 200)
        content = data.decode("utf-8")
        self.assertIn("<!DOCTYPE html>", content)

    def test_cors_headers(self):
        status, headers, _ = self.get("/api/parks")
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")


if __name__ == "__main__":
    unittest.main()
