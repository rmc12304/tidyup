import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from tidyup.core import Engine
from tidyup.server import create_server
from tidyup.storage import Store


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tidyup-api-")
        self.store = Store(Path(self.tmp.name) / "data")
        self.engine = Engine(self.store)
        self.server = create_server(self.engine, 0)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        if self.engine.worker:
            self.engine.worker.join()
        self.store.close()
        self.tmp.cleanup()

    def request(self, path="/api/state", method="GET", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        status, result_headers = response.status, dict(response.getheaders())
        connection.close()
        return status, payload, result_headers

    def headers(self):
        state = json.loads(self.request()[1])
        return {"Origin": self.origin, "X-Tidyup-CSRF": state["csrf"], "Content-Type": "application/json"}

    def test_loopback_host_origin_csrf(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertEqual(self.request(headers={"Host": "evil.test"})[0], 403)
        self.assertEqual(self.request(headers={"Origin": "https://evil.test"})[0], 403)
        self.assertEqual(self.request("/api/scan", "POST", {}, {"Content-Type": "application/json"})[0], 403)
        self.assertEqual(self.request("/api/scan", "POST", {}, self.headers())[0], 400)

    def test_functional_scan_api_and_no_arbitrary_path_execute(self):
        base = Path(self.tmp.name)
        source, reference = base / "source", base / "reference"
        source.mkdir(); reference.mkdir()
        (source / "<script>alert(1)</script>".replace("/", "_")).write_bytes(b"fixture")
        (reference / "copy").write_bytes(b"fixture")
        headers = self.headers()
        self.assertEqual(self.request("/api/config", "POST", {"source": str(source), "references": [str(reference)], "recursive": False}, headers)[0], 200)
        self.assertEqual(self.request("/api/scan", "POST", {}, headers)[0], 200)
        self.engine.worker.join()
        job = json.loads(self.request()[1])["job"]
        self.assertEqual(job["summary"]["verified"], 1)
        self.assertEqual(self.request("/api/execute", "POST", {"path": str(source)}, headers)[0], 400)
        status, payload, _ = self.request("/api/plan", "POST", {"selections": [{"id": job["items"][0]["id"], "exception": False}]}, headers)
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(payload)["executable"])

    def test_static_security_headers_and_invalid_pagination(self):
        status, payload, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b'lang="pt-BR"', payload)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("/../storage.py")[0], 404)
        self.assertEqual(self.request("/api/state?offset=bad")[0], 400)


if __name__ == "__main__":
    unittest.main()
