"""Tests hors-ligne (stdlib) : validation des paramètres, anti path-traversal, CORS,
chargement du journal de sessions. Lancer : python -m unittest discover -s tests"""
import http.client
import os
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server  # noqa: E402


class ParamTests(unittest.TestCase):
    def test_model(self):
        self.assertEqual(server._clean_model("meteofrance_wave"), "meteofrance_wave")
        self.assertIsNone(server._clean_model(""))
        self.assertIsNone(server._clean_model(None))
        self.assertIsNone(server._clean_model("../../etc/passwd"))
        self.assertIsNone(server._clean_model("x&past_days=9999"))

    def test_level(self):
        self.assertEqual(server._clean_level("confirme"), "confirme")
        self.assertEqual(server._clean_level("<script>"), "debutant")

    def test_sessions_path(self):
        old = os.environ.get("SURFCAST_SESSIONS")
        try:
            os.environ["SURFCAST_SESSIONS"] = "/data/sessions.json"
            self.assertEqual(server._sessions_path(), "/data/sessions.json")
            del os.environ["SURFCAST_SESSIONS"]
            self.assertTrue(server._sessions_path().endswith(("sessions.json", "sessions.example.json")))
        finally:
            if old is not None:
                os.environ["SURFCAST_SESSIONS"] = old

    def test_example_is_valid(self):
        data = server.sess_mod.load_sessions(os.path.join(ROOT, "sessions.example.json"))
        for s in data["sessions"]:
            self.assertIn(s["spot"], server.SPOTS)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        static = os.path.join(cls.tmp.name, "static")
        os.makedirs(static)
        with open(os.path.join(static, "index.html"), "w") as f:
            f.write("<html>ok</html>")
        os.makedirs(os.path.join(cls.tmp.name, "static2"))
        with open(os.path.join(cls.tmp.name, "static2", "secret.txt"), "w") as f:
            f.write("secret")
        cls._old_static = server.STATIC_DIR
        server.STATIC_DIR = static
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        server.STATIC_DIR = cls._old_static
        cls.tmp.cleanup()

    def get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=10)
        c.request("GET", path)
        r = c.getresponse()
        return r, r.read()

    def test_spots_no_wildcard_cors(self):
        r, body = self.get("/api/spots")
        self.assertEqual(r.status, 200)
        self.assertIsNone(r.getheader("Access-Control-Allow-Origin"))
        self.assertEqual(r.getheader("X-Content-Type-Options"), "nosniff")

    def test_static_index(self):
        r, body = self.get("/")
        self.assertEqual(r.status, 200)
        self.assertIn(b"ok", body)

    def test_traversal_blocked(self):
        for p in ("/../static2/secret.txt", "/..%2fstatic2/secret.txt", "/../../server.py"):
            r, body = self.get(p)
            self.assertNotIn(b"secret", body, p)
            self.assertNotIn(b"ThreadingHTTPServer", body, p)


if __name__ == "__main__":
    unittest.main()
