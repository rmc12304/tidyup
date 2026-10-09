"""Teste opt-in do Engine real com adaptador Windows e fixtures próprias.

Sem caminhos de entrada, servidor ou ativação da limpeza de arquivos pessoais.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile
import time
import uuid

from . import __version__
from .core import Engine
from .filesystem import full_hash
from .native import WindowsFixtureTrash
from .storage import Store


def run(report_dir):
    report_dir = Path(report_dir).expanduser().resolve()
    checkout = Path(__file__).resolve().parent.parent
    if report_dir == checkout or report_dir.is_relative_to(checkout):
        raise ValueError("Relatórios devem ficar fora do pacote/repositório.")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"windows-flow-{uuid.uuid4().hex}.json"
    report = {"schema_version": 1, "app_version": __version__, "python_version": platform.python_version(),
              "synthetic_only": True, "status": "not_executed", "started_at": time.time(),
              "assertions": {}, "operations": [], "restoration_tested": False, "ui_tested": False}

    def persist():
        temporary = report_path.with_suffix(".new")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(report_path)

    persist()
    if os.name != "nt":
        report["reason"] = "Não executado: requer Windows nativo. Nenhuma fixture movimentada."
        persist()
        return report, report_path
    store = engine = None
    try:
        root = Path(tempfile.mkdtemp(prefix="tidyup-windows-flow-")).resolve()
        source, reference = root / "source", root / "reference"
        source.mkdir(); reference.mkdir()
        report["fixture_root"] = str(root)
        selected_names = ("arquivo-um.txt", "acentuação 日本語 dois.txt")
        expected = {}
        for name in (*selected_names, "não-selecionado.txt", "alterar-origem.txt", "alterar-referencia.txt"):
            content = f"Tidyup: somente fixture. {root.name}: {name}\n".encode()
            (source / name).write_bytes(content)
            (reference / name).write_bytes(content)
            expected[name] = hashlib.sha256(content).hexdigest()
        store = Store(root / "data")
        adapter = WindowsFixtureTrash(root)
        engine = Engine(store, adapter)
        engine.configure(str(source), [str(reference)])

        def plan_for(names):
            engine.start()
            engine.worker.join(30)
            if engine.worker.is_alive():
                engine.cancel.set()
                raise RuntimeError("Inventário da fixture excedeu o tempo previsto.")
            snapshot = engine.snapshot()
            if snapshot["status"] != "completed":
                raise RuntimeError("Inventário da fixture não concluiu.")
            selections = [{"id": item["id"], "exception": False} for item in snapshot["items"] if item["name"] in names]
            if len(selections) != len(names):
                raise RuntimeError("Inventário não encontrou todos os itens esperados.")
            return engine.plan(selections)

        plan = plan_for(selected_names)
        report.update(status="intent", plan_id=plan["id"])
        persist()
        batch = engine.execute(plan["id"])
        report["operations"].append(batch)
        report["assertions"]["selected_items_recycled"] = len(batch["results"]) == 2 and all(item["status"] == "success" for item in batch["results"])
        report["assertions"]["unselected_preserved"] = full_hash(source / "não-selecionado.txt", source) == expected["não-selecionado.txt"]
        report["assertions"]["all_references_preserved"] = all(full_hash(reference / name, reference) == digest for name, digest in expected.items())
        report["assertions"]["same_plan_not_reexecuted"] = engine.execute(plan["id"]) == batch
        persist()
        store.close()
        store = None
        store = Store(root / "data")
        engine = Engine(store, WindowsFixtureTrash(root))
        report["assertions"]["restart_retains_result"] = engine.execute(plan["id"]) == batch

        for name, changed_role in (("alterar-origem.txt", source), ("alterar-referencia.txt", reference)):
            plan = plan_for((name,))
            changed = changed_role / name
            changed.write_bytes(b"Alteracao sintetica intencional apos a revisao.\n")
            operation = engine.execute(plan["id"])
            report["operations"].append(operation)
            key = "changed_source_blocked" if changed_role == source else "changed_reference_blocked"
            report["assertions"][key] = len(operation["results"]) == 1 and operation["results"][0]["status"] == "blocked" and (source / name).exists()
            persist()
        report["status"] = "passed" if all(report["assertions"].values()) else "not_confirmed"
        report["reason"] = "Fluxo do executor com fixtures; não testa interface, restauração ou todos os cenários Windows. Limpeza normal não habilitada."
    except Exception as exc:
        report.update(status="uncertain" if report["status"] == "intent" else "blocked", reason=str(exc))
    finally:
        if engine and engine.worker and engine.worker.is_alive():
            engine.cancel.set()
            engine.worker.join()  # encerrar leitor antes de fechar banco
        if store:
            store.close()
    report["finished_at"] = time.time()
    persist()
    return report, report_path
