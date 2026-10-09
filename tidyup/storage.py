"""Estado operacional fora do checkout; gravações SQLite transacionais."""
import json
import os
import sqlite3
import threading
from pathlib import Path

from . import SCHEMA_VERSION


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        repo = Path(__file__).resolve().parent.parent
        if self.directory == repo or self.directory.is_relative_to(repo):
            raise ValueError("DATA_DIR deve ficar fora do repositório.")
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.process_lock = os.fdopen(os.open(self.directory / "instance.lock", os.O_RDWR | os.O_CREAT, 0o600), "a+b")
        try:
            if os.name == "posix":
                import fcntl
                fcntl.flock(self.process_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                import msvcrt
                self.process_lock.write(b"0")
                self.process_lock.flush()
                self.process_lock.seek(0)
                msvcrt.locking(self.process_lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            self.process_lock.close()
            raise ValueError("DATA_DIR já está em uso por outra instância.") from exc
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.directory / "state.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            raise ValueError("Esquema incompatível. Faça backup antes de migrar.")
        self.db.execute("CREATE TABLE IF NOT EXISTS documents (kind TEXT, id TEXT, value TEXT, PRIMARY KEY(kind,id))")
        self.db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self.db.commit()
        if os.name != "nt":
            os.chmod(self.directory / "state.sqlite3", 0o600)

    def put(self, kind, key, value):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?)", (kind, key, json.dumps(value, ensure_ascii=True)))

    def get(self, kind, key):
        with self.lock:
            row = self.db.execute("SELECT value FROM documents WHERE kind=? AND id=?", (kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, kind):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute("SELECT value FROM documents WHERE kind=? ORDER BY rowid DESC", (kind,))]

    def close(self):
        self.db.close()
        self.process_lock.close()
