"""
Tests for Disney Wait Times frontend (index.html structure, DOM integrity, and scripts).
"""

import html.parser
import os
import re
import subprocess
import unittest


class DOMExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.element_ids = set()
        self.scripts = []
        self._current_tag = None
        self._script_buffer = []

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        attr_dict = dict(attrs)
        if "id" in attr_dict:
            self.element_ids.add(attr_dict["id"])
        if tag == "script":
            self._script_buffer = []

    def handle_data(self, data):
        if self._current_tag == "script":
            self._script_buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script_buffer:
            self.scripts.append("".join(self._script_buffer))
            self._script_buffer = []
        self._current_tag = None


class TestFrontendIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
        with open(cls.html_path, "r", encoding="utf-8") as f:
            cls.html_content = f.read()

        cls.parser = DOMExtractor()
        cls.parser.feed(cls.html_content)

    def test_html_file_exists(self):
        self.assertTrue(os.path.exists(self.html_path))
        self.assertGreater(len(self.html_content), 1000)

    def test_essential_dom_elements_exist(self):
        required_ids = [
            "parkSelect",
            "modeBoxBtn",
            "modeBoardBtn",
            "settingsBtn",
            "fullscreenBtn",
            "parkClockBtn",
            "parkClockDisplay",
            "parkTimezoneLabel",
            "statOpenRides",
            "statTotalRides",
            "statAvgWait",
            "statMaxWait",
            "boxView",
            "boxProgressBar",
            "boxRideTitle",
            "boxWaitNumber",
            "boxWaitUnits",
            "boxWaitStatus",
            "boxFavBtn",
            "btnPrev",
            "btnNext",
            "btnPlayPause",
            "boardView",
            "boardGridContainer",
            "modeFireworksBtn",
            "fireworksView",
            "fireworksFeedSelect",
            "fireworksIframe",
            "fireworksReturnBtn",
            "settingsModal",
            "closeSettingsBtn",
            "settingTimezone",
            "settingSpeed",
            "settingBezel",
            "settingFilter",
        ]
        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(element_id, self.parser.element_ids, f"Missing required element #{element_id}")

    def test_fireworks_view_elements(self):
        """Verify fireworks view and preset feeds exist."""
        self.assertIn("modeFireworksBtn", self.parser.element_ids)
        self.assertIn("fireworksIframe", self.parser.element_ids)
        self.assertIn("Happily Ever After", self.html_content)
        self.assertIn("Luminous", self.html_content)
        self.assertIn("Wondrous Journeys", self.html_content)

    def test_timezone_default_cst(self):
        """Verify Central Time (America/Chicago) is the default configured timezone."""
        self.assertIn('America/Chicago', self.html_content)
        self.assertIn('(CST)', self.html_content)
        # Check settingTimezone option exists
        self.assertRegex(self.html_content, r'<option\s+value="America/Chicago"\s+selected>')

    def test_javascript_syntax_valid(self):
        """Validate JavaScript syntax inside the HTML file."""
        self.assertGreater(len(self.parser.scripts), 0, "No script tag found in HTML")
        js_code = self.parser.scripts[0]

        # Use node --check if node is available
        try:
            res = subprocess.run(["node", "--check"], input=js_code, text=True, capture_output=True)
            self.assertEqual(res.returncode, 0, f"JavaScript syntax error: {res.stderr}")
        except FileNotFoundError:
            # Fallback if node is not installed: basic regex checks
            self.assertIn("function startParkClock", js_code)
            self.assertIn("function loadParkData", js_code)


if __name__ == "__main__":
    unittest.main()
