"""The built front end is served at / and its files under /static/ (option A of 2 November 2026)."""
import re

from django.conf import settings
from django.test import SimpleTestCase


class FrontendTests(SimpleTestCase):
    def test_index_page_is_served(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '<div id="root"></div>')
        self.assertContains(r, "<title>Global Mobility Estimator</title>")

    def test_built_files_exist_for_every_reference(self):
        html = (settings.FRONTEND_DIST / "index.html").read_text(encoding="utf-8")
        refs = re.findall(r'(?:src|href)="/static/([^"]+)"', html)
        self.assertTrue(any(ref.endswith(".js") for ref in refs))
        self.assertTrue(any(ref.endswith(".css") for ref in refs))
        for ref in refs:
            self.assertTrue((settings.FRONTEND_DIST / ref).exists(), ref)
