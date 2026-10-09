"""Inicialização sem terminal; browser e serviço usam a mesma máquina."""
import json
import os
import secrets
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

from .core import Engine
from .server import create_server
from .storage import Store


def default_data_dir():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise ValueError("O Windows não forneceu LOCALAPPDATA. Configure DATA_DIR.")
        return Path(base) / "Tidyup"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "tidyup"


def reopen_existing(directory, opener=webbrowser.open):
    """Só reutilizar uma instância que prove o identificador salvo localmente."""
    try:
        metadata = json.loads((Path(directory) / "instance.json").read_text())
        port = metadata["port"]
        if type(port) is not int or not 1 <= port <= 65535:
            return False
        url = f"http://127.0.0.1:{port}"
        # Ignorar proxies do processo apenas para esta conexão de loopback.
        request = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with request.open(url + "/api/instance", timeout=2) as response:
            live = json.load(response)
        if live.get("app") != "tidyup" or live.get("instance_id") != metadata["instance_id"]:
            return False
        return bool(opener(url))
    except (OSError, ValueError, KeyError):
        return False


def notify(message):
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "Tidyup", 0x10)
    elif sys.stderr is not None:
        print(message, file=sys.stderr)


def run(directory=None, opener=webbrowser.open, ready=None):
    directory = Path(directory or os.environ.get("DATA_DIR") or default_data_dir()).expanduser().resolve()
    if reopen_existing(directory, opener):
        return
    try:
        store = Store(directory)
    except ValueError:
        if reopen_existing(directory, opener):
            return
        raise
    engine = Engine(store)
    server = None
    worker = None
    metadata_path = directory / "instance.json"
    try:
        server = create_server(engine, 0)
        server.instance_id = secrets.token_hex(16)
        metadata = {"port": server.server_port, "instance_id": server.instance_id}
        temporary = directory / "instance.new"
        temporary.write_text(json.dumps(metadata), encoding="utf-8")
        if os.name == "posix":
            temporary.chmod(0o600)
        temporary.replace(metadata_path)
        # Navegador pode conectar assim que o socket está ouvindo; a thread
        # serve_forever começa antes de aguardar interação do usuário.
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        url = f"http://127.0.0.1:{server.server_port}"
        if ready:
            ready(url)
        if not opener(url):
            server.shutdown()
            worker.join()
            raise RuntimeError("Não foi possível abrir o navegador padrão. Confira sua configuração de navegador.")
        worker.join()
    finally:
        engine.cancel.set()
        engine.execution_cancel.set()
        if worker and worker.is_alive():
            server.shutdown()
            worker.join()
        if server:
            server.server_close()
        if engine.worker:
            engine.worker.join()
        if metadata_path.exists() and server:
            try:
                if json.loads(metadata_path.read_text())["instance_id"] == server.instance_id:
                    metadata_path.unlink()  # Só metadado próprio; nunca um arquivo inventariado.
            except (OSError, ValueError, KeyError):
                pass
        store.close()


def main():
    try:
        if sys.version_info < (3, 12):
            raise RuntimeError("Instale Python 3.12 ou mais recente em python.org e abra o inicializador novamente.")
        run()
    except Exception as exc:
        notify(f"Não foi possível iniciar o aplicativo.\n\n{exc}")


if __name__ == "__main__":
    main()
