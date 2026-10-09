import argparse
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .core import Engine
from .filesystem import Blocked
from .storage import Store
from . import __version__


STATIC = Path(__file__).parent / "static"


def create_server(engine, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            # Não registrar caminhos pessoais ou corpos de requisição.
            pass

        def reply(self, status, value, content_type="application/json; charset=utf-8"):
            if content_type.startswith("application/json") and isinstance(value, dict):
                value = {"schema_version": 1, **value}
                if status >= 400:
                    value["code"] = "access_denied" if status == 403 else "request_rejected" if status < 500 else "internal_error"
            payload = json.dumps(value, ensure_ascii=True).encode() if content_type.startswith("application/json") else value
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(payload)

        def guard(self, mutable=False):
            expected = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected:
                self.reply(403, {"error": "Host inesperado. Use o endereço 127.0.0.1 informado."})
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin != f"http://{expected}":
                self.reply(403, {"error": "Origem não autorizada."})
                return False
            if mutable and (origin != f"http://{expected}" or not secrets.compare_digest(self.headers.get("X-Tidyup-CSRF", ""), token)):
                self.reply(403, {"error": "Requisição sem autorização CSRF."})
                return False
            return True

        def do_GET(self):
            if not self.guard():
                return
            parsed = urlsplit(self.path)
            try:
                if parsed.path == "/api/instance":
                    self.reply(200, {"app": "tidyup", "version": __version__, "instance_id": self.server.instance_id})
                elif parsed.path == "/api/state":
                    query = parse_qs(parsed.query)
                    offset = max(0, int(query.get("offset", [0])[0]))
                    self.reply(200, {"csrf": token, "capabilities": engine.capabilities(), "config": engine.store.get("config", "current"), "job": engine.snapshot(offset, 50)})
                elif parsed.path == "/api/history":
                    self.reply(200, {"operations": engine.store.all("operation")[:100]})
                elif parsed.path in ("/", "/app.js", "/style.css"):
                    filename, content_type = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}[parsed.path]
                    self.reply(200, (STATIC / filename).read_bytes(), content_type)
                else:
                    self.reply(404, {"error": "Rota não encontrada."})
            except (ValueError, OSError) as exc:
                self.reply(400, {"error": str(exc)})

        def do_POST(self):
            if not self.guard(mutable=True):
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 128 * 1024 or self.headers.get("Content-Type") != "application/json":
                    raise Blocked("Corpo JSON inválido ou grande demais.")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise Blocked("Objeto JSON obrigatório.")
                path = urlsplit(self.path).path
                if path == "/api/config":
                    if set(body) != {"source", "references", "recursive"}:
                        raise Blocked("Campos de configuração inválidos.")
                    result = engine.configure(**body)
                elif path in ("/api/scan", "/api/resume") and not body:
                    result = {"job_id": engine.start()}
                elif path == "/api/cancel" and not body:
                    engine.cancel.set()
                    engine.execution_cancel.set()
                    result = {"requested": True}
                elif path == "/api/shutdown" and not body:
                    engine.cancel.set()
                    engine.execution_cancel.set()
                    self.reply(200, {"stopping": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                elif path == "/api/native-diagnostics" and not body:
                    diagnostic = getattr(engine.adapter, "diagnostics", None)
                    result = diagnostic() if diagnostic else {"available": False, "operational": False, "reason": "Diagnóstico disponível somente em Python nativo Windows. Nenhum arquivo foi movido."}
                elif path == "/api/plan" and set(body) == {"selections"}:
                    result = engine.plan(body["selections"])
                elif path == "/api/execute" and set(body) == {"plan_id"} and isinstance(body["plan_id"], str):
                    result = engine.execute(body["plan_id"])
                else:
                    raise Blocked("Rota ou campos inválidos. Caminhos não autorizam execução.")
                self.reply(200, result)
            except (ValueError, OSError, TypeError, KeyError) as exc:
                self.reply(400, {"error": str(exc)})
            except Exception:
                self.reply(500, {"error": "Falha interna. Consulte o histórico antes de repetir uma operação."})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = False
    server.instance_id = secrets.token_hex(16)
    return server


def main():
    parser = argparse.ArgumentParser(description="Tidyup: revisão local de arquivos; sem telemetria")
    parser.add_argument("--data-dir", default=os.environ.get("DATA_DIR", str(Path.home() / ".local" / "share" / "tidyup")))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    store = Store(args.data_dir)
    engine = Engine(store)
    server = create_server(engine, args.port)
    print(f"Tidyup em http://127.0.0.1:{server.server_port} — Ctrl+C para encerrar.", flush=True)
    print(engine.adapter.reason, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        engine.cancel.set()
        engine.execution_cancel.set()
        server.server_close()
        if engine.worker:
            engine.worker.join()
        store.close()


if __name__ == "__main__":
    main()
