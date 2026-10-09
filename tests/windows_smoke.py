"""Opt-in Windows: fixtures de leitura e COM. NÃO testa movimentação/restauração."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

from tidyup.filesystem import full_hash
from tidyup.windows import guarded_fd, probe_ifileoperation


def main():
    if os.name != "nt" or os.environ.get("TIDYUP_WINDOWS_FIXTURE_TESTS") != "1":
        raise SystemExit("Requer Windows nativo e TIDYUP_WINDOWS_FIXTURE_TESTS=1. Nenhum teste foi executado.")
    with tempfile.TemporaryDirectory(prefix="tidyup-windows-fixture-") as tmp:
        root = Path(tmp)
        folder = root
        for i in range(14):
            folder /= f"fixture-unicode-ç-{i}"
        folder.mkdir(parents=True)
        source = folder / "日本語 fixture.txt"
        source.write_bytes(b"fixture-only")
        assert len(str(source)) > 260
        assert full_hash(source, root) == hashlib.sha256(b"fixture-only").hexdigest()
        with guarded_fd(source):
            try:
                source.rename(folder / "changed.txt")
            except PermissionError:
                pass
            else:
                raise AssertionError("O handle não impediu troca do nome.")
        diagnostic = probe_ifileoperation()
        assert diagnostic["available"], diagnostic
        assert diagnostic["operational"] is False
        print(json.dumps({"read_smoke": "passed", "COM": diagnostic, "recycle_test": "not_executed", "restore_test": "not_executed"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
