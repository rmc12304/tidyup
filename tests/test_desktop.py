import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlsplit
import zipfile

from tidyup.desktop import reopen_existing, run
from tidyup.windows import directory_guard, extended_path, GUID, probe_ifileoperation
from tools.build_local import build


class DesktopTests(unittest.TestCase):
    def request(self, url, path, body=None, token=None):
        parsed = urlsplit(url)
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        headers = {} if body is None else {"Origin": url, "Content-Type": "application/json", "X-Tidyup-CSRF": token}
        conn.request("GET" if body is None else "POST", path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse()
        result = json.loads(response.read())
        self.assertEqual(response.status, 200, result)
        conn.close()
        return result

    def test_open_reopen_and_shutdown_without_terminal(self):
        with tempfile.TemporaryDirectory(prefix="tidyup-desktop-") as tmp:
            opened, errors = [], []
            ready = threading.Event()
            def opener(url):
                opened.append(url)
                ready.set()
                return True
            def launch():
                try:
                    run(tmp, opener=opener)
                except Exception as exc:
                    errors.append(exc)
            worker = threading.Thread(target=launch)
            worker.start()
            self.assertTrue(ready.wait(5))
            try:
                url = opened[0]
                state = self.request(url, "/api/state")
                run(tmp, opener=opener)
                self.assertEqual(opened, [url, url])
                result = self.request(url, "/api/native-diagnostics", {}, state["csrf"])
                self.assertFalse(result["operational"])
                self.request(url, "/api/shutdown", {}, state["csrf"])
                worker.join(5)
                self.assertFalse(worker.is_alive())
                self.assertFalse((Path(tmp) / "instance.json").exists())
                self.assertFalse(errors, errors)
            finally:
                if worker.is_alive():
                    self.request(opened[0], "/api/shutdown", {}, state["csrf"])
                    worker.join(5)

    def test_stale_or_hostile_instance_metadata(self):
        with tempfile.TemporaryDirectory(prefix="tidyup-instance-") as tmp:
            path = Path(tmp) / "instance.json"
            path.write_text('{"port":"https://remote.test","instance_id":"fake"}')
            self.assertFalse(reopen_existing(tmp, opener=lambda _: self.fail("Não abrir destino remoto")))

    def test_html_and_archive_exclude_operational_data(self):
        with tempfile.TemporaryDirectory(prefix="tidyup-build-") as tmp:
            html, archive = build(tmp)
            text = html.read_text()
            self.assertIn('<style>', text)
            self.assertIn('location.protocol===', text)
            self.assertNotIn('src="/app.js"', text)
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertIn("tidyup-local/Abrir Tidyup.cmd", names)
                self.assertIn("tidyup-local/Tidyup.html", names)
                self.assertFalse(any(name.endswith((".sqlite3", ".pyc", "instance.json")) or "/.git/" in name for name in names))


class WindowsContractTests(unittest.TestCase):
    def test_long_unicode_paths_and_invalid_destinations(self):
        path = "C:\\dados\\" + "pasta\\" * 50 + "日本語 açao.txt"
        self.assertTrue(extended_path(path).startswith("\\\\?\\C:\\"))
        for invalid in ("relative.txt", "\\\\server\\share\\item", "C:\\dados\\..\\item", "C:\\item:stream"):
            with self.assertRaises(ValueError):
                extended_path(invalid)

    def test_directory_handles_close_on_interruption(self):
        class FakeAPI:
            def __init__(self):
                self.opened, self.closed = [], []
            def open(self, path, directory):
                self.opened.append(str(path))
                if str(path).endswith("unsafe"):
                    raise ValueError("junction")
                return len(self.opened)
            def close(self, handle):
                self.closed.append(handle)
        api = FakeAPI()
        with self.assertRaises(ValueError):
            with directory_guard("C:\\safe\\unsafe", api):
                self.fail("Não entrar em pasta não validada")
        self.assertEqual(api.closed, [2, 1])

    def test_com_guid_layout_and_linux_probe(self):
        guid = GUID.parse("3ad05575-8857-4850-9277-11b85bdb8e09")
        self.assertEqual(guid.data1, 0x3ad05575)
        self.assertFalse(probe_ifileoperation()["available"])
