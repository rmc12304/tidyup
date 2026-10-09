"""Teste real opt-in de IFileOperation, limitado a fixture recém-criada.

Não é o adaptador de produção. Nunca recebe raízes ou seleções do aplicativo.
"""
import hashlib
import json
import os
import platform
from pathlib import Path
import tempfile
import time
import uuid

from .filesystem import full_hash, safe_stat, signature
from . import __version__

from .windows_recycle import (RECYCLE_FLAGS, ProgressSink, classify, perform_recycle)


def perform_fixture_recycle(source, verify):
    """Restrição adicional do teste básico, preservada ao compartilhar COM."""
    source = Path(source)
    fixture_root = source.parent.parent
    if (source.resolve() != source or source.name != "arquivo-sintetico.txt"
            or source.parent.name != "source" or not fixture_root.name.startswith("tidyup-native-trash-test-")
            or fixture_root.parent != Path(tempfile.gettempdir()).resolve()):
        raise ValueError("Operação nativa recusada: só a fixture própria em TEMP pode ser reciclada.")
    return perform_recycle(source, verify)


def run(report_dir):
    report_dir = Path(report_dir).expanduser().resolve()
    checkout = Path(__file__).resolve().parent.parent
    if report_dir == checkout or report_dir.is_relative_to(checkout):
        raise ValueError("Relatório operacional deve ficar fora do repositório/pacote.")
    report_dir.mkdir(parents=True, exist_ok=True)
    test_id = uuid.uuid4().hex
    report_path = report_dir / f"recycle-test-{test_id}.json"
    report = {"schema_version": 1, "app_version": __version__, "python_version": platform.python_version(), "test_id": test_id, "started_at": time.time(), "status": "not_executed", "synthetic_only": True}
    def persist():
        temporary = report_path.with_suffix(".new")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(report_path)
    persist()
    if os.name != "nt":
        report["reason"] = "Teste nativo não executado: este ambiente é Linux/POSIX, sem sessão Windows."
        persist()
        return report, report_path
    try:
        root = Path(tempfile.mkdtemp(prefix="tidyup-native-trash-test-")).resolve()
        origin, reference = root / "source", root / "reference"
        origin.mkdir(); reference.mkdir()
        source, preserved = origin / "arquivo-sintetico.txt", reference / "copia-sintetica.txt"
        content = f"Tidyup: fixture sintética de teste, sem dados pessoais.\nID: {test_id}\n".encode()
        source.write_bytes(content); preserved.write_bytes(content)
        expected_hash = hashlib.sha256(content).hexdigest()
        source_identity = signature(safe_stat(source, origin))
        reference_identity = signature(safe_stat(preserved, reference))
        def verify(path):
            if not path or Path(path).resolve() != source or not source.is_relative_to(root):
                raise ValueError("O Shell tentou operar fora da fixture sintética autorizada.")
            if full_hash(source, origin, source_identity) != expected_hash:
                raise ValueError("Fixture origem alterada; bloquear.")
            if full_hash(preserved, reference, reference_identity) != expected_hash:
                raise ValueError("Fixture de referência alterada; bloquear.")
        verify(str(source))
        report.update(status="intent", fixture_root=str(root), source=str(source), reference=str(preserved), expected_sha256=expected_hash,
                      policy="Revalidar origem/referência imediatamente antes; aceitar intervalo entre verificação e chamada nativa.")
        persist()  # Intenção durável ANTES de solicitar a operação.
        native = perform_fixture_recycle(source, verify)
        report["native"] = native
        report["original_absent"] = not os.path.lexists(source)
        recycled_hash = None
        for event in native["events"]:
            if event.get("stage") == "post_delete" and event.get("recycled_path"):
                recycled = Path(event["recycled_path"])
                try:
                    # Ler só o item sintético retornado pelo callback; não varrer Lixeira.
                    recycled_hash = full_hash(recycled, recycled.parent)
                except (OSError, ValueError) as exc:
                    report["recycled_read_error"] = str(exc)
                    if getattr(exc, "details", None):
                        report["recycled_read_error_details"] = exc.details
        report["recycled_sha256"] = recycled_hash
        reference_hash = full_hash(preserved, reference, reference_identity)
        report["reference_sha256"] = reference_hash
        report["status"] = classify(native, report["original_absent"], recycled_hash, expected_hash, reference_hash)
        report["reason"] = "Consulte HRESULT, callback, hash reciclado e referência no relatório. Restauração pelo SO não foi testada."
    except Exception as exc:
        report.update(status="uncertain" if report["status"] == "intent" else "blocked", reason=str(exc))
    report["finished_at"] = time.time()
    persist()
    return report, report_path
