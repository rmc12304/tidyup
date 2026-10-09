"""Medição local reproduzível com 136 MiB de fixtures, sem arquivos pessoais."""
import json
import platform
import tempfile
import time
from pathlib import Path

from tidyup.core import Engine
from tidyup.storage import Store


def main():
    with tempfile.TemporaryDirectory(prefix="tidyup-bench-") as tmp:
        root = Path(tmp)
        source, ref = root / "source", root / "reference"
        source.mkdir(); ref.mkdir()
        chunk = b"synthetic-fixture" * (1024 * 64)
        for folder in (source, ref):
            with (folder / "large").open("wb") as out:
                for _ in range(64):
                    out.write(chunk)
        store = Store(root / "data")
        engine = Engine(store)
        engine.configure(str(source), [str(ref)])
        started = time.perf_counter()
        engine.start(); engine.worker.join()
        elapsed = time.perf_counter() - started
        job = engine.snapshot()
        assert job["status"] == "completed" and job["summary"]["verified"] == 1
        print(json.dumps({"platform": platform.platform(), "python": platform.python_version(), "files": 2, "bytes_read": job["bytes_read"], "seconds": round(elapsed, 4), "hash_concurrency": 1, "cache": "cold application cache; OS cache warm from fixture creation", "note": "Não extrapolar para Downloads reais ou armazenamento em nuvem."}))
        store.close()


if __name__ == "__main__":
    main()
