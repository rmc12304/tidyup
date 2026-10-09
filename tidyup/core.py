import copy
import hashlib
import os
import secrets
import stat
import threading
import time
from pathlib import Path

from .filesystem import Blocked, directory_entries, full_hash, safe_stat, signature, validate_roots
from .native import default_adapter


def opaque():
    return secrets.token_hex(16)


class Engine:
    def __init__(self, store, adapter=None):
        self.store = store
        self.adapter = adapter or default_adapter()
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.worker = None
        self.execution_cancel = threading.Event()
        if callable(getattr(self.adapter, "bind_cancel", None)):
            self.adapter.bind_cancel(self.execution_cancel)
        self.executing = False
        interrupted_job = store.get("job", "current")
        if interrupted_job and interrupted_job["status"] == "running":
            interrupted_job.update(status="cancelled", stage="Processo reiniciado; retome para revalidar o inventário.")
            store.put("job", "current", interrupted_job)
        # Intent durável sem resultado não deve jamais ser reenviado automaticamente.
        for op in store.all("operation"):
            changed = False
            for result in op["results"]:
                if result["status"] == "intent":
                    result.update(status="uncertain", reason="Processo interrompido após intenção. Reconciliação manual necessária; não repetir.")
                    changed = True
            if changed or op["status"] == "running":
                op["status"] = "interrupted"
                store.put("operation", op["id"], op)

    def capabilities(self):
        return {"schema_version": 1, "trash_supported": self.adapter.supported, "reason": self.adapter.reason, "platform": os.name}

    def configure(self, source, references, recursive=False):
        if not isinstance(recursive, bool):
            raise Blocked("Recursão deve ser uma escolha explícita booleana.")
        with self.lock:
            if self.worker and self.worker.is_alive() or self.executing:
                raise Blocked("Aguarde ou cancele a operação atual.")
            config = validate_roots(source, references, self.store.directory)
            config.update(recursive=recursive, schema_version=1, id=opaque())
            previous = self.store.get("config", "current")
            if previous:
                self.store.put("config_backup", opaque(), previous)
            self.store.put("config", "current", config)
            job = self.store.get("job", "current")
            if job:
                job.update(status="invalidated", stage="Configuração alterada; inicie novo inventário.")
                self.store.put("job", "current", job)
            return config

    def start(self):
        with self.lock:
            if self.worker and self.worker.is_alive() or self.executing:
                raise Blocked("Há uma operação em andamento.")
            config = self.store.get("config", "current")
            if not config:
                raise Blocked("Configure e valide as raízes primeiro.")
            fresh = validate_roots(config["source"], config["references"], self.store.directory)
            if fresh["root_identities"] != config["root_identities"]:
                raise Blocked("Identidade de raiz alterada; configure novamente.")
            job = {"schema_version": 1, "id": opaque(), "config": config, "status": "running", "stage": "inventário", "files": [], "errors": [], "bytes_read": 0, "started_at": time.time()}
            self.cancel.clear()
            self.store.put("job", "current", job)
            self.worker = threading.Thread(target=self._scan, args=(job,), daemon=True)
            self.worker.start()
            return job["id"]

    def snapshot(self, offset=0, limit=100):
        job = self.store.get("job", "current")
        if not job:
            return None
        files = job.pop("files")
        sources = [f for f in files if f["role"] == "source"]
        job["summary"] = {"files": len(files), "source_files": len(sources), "bytes": sum(f["size"] for f in files), "verified": sum(f["state"] == "verified" for f in sources), "blocked": sum(f["state"] == "blocked" for f in files)}
        by_id = {f["id"]: f for f in files}
        job["items"] = [{**f, "references": [by_id[r] for r in f.get("matches", [])]} for f in sources[offset:offset + limit]]
        job.update(offset=offset, limit=limit, total=len(sources))
        return job

    def _save_job(self, job, force=True):
        now = time.monotonic()
        if force or now - getattr(self, "last_job_save", 0) >= .25:
            self.store.put("job", "current", job)
            self.last_job_save = now

    def _scan(self, job):
        try:
            config = job["config"]
            for role, roots in [("source", [config["source"]]), ("reference", config["references"])]:
                for root in roots:
                    stack = [Path(root)]
                    while stack:
                        if self.cancel.is_set():
                            raise InterruptedError()
                        folder = stack.pop()
                        # Revalidar ancestrais antes de percorrer; nunca seguir links.
                        if folder.resolve() != folder:
                            raise Blocked("Pasta redirecionada durante a varredura.")
                        try:
                            with directory_entries(folder) as entries:
                                # DirEntry.stat precisa do descritor durante este bloco.
                                for entry in entries:
                                    path = str(folder / entry.name)
                                    if self.cancel.is_set():
                                        raise InterruptedError()
                                    try:
                                        st = entry.stat(follow_symlinks=False)
                                        reparse = getattr(st, "st_file_attributes", 0) & 0x400
                                        if stat.S_ISDIR(st.st_mode) and not reparse:
                                            if config["recursive"]:
                                                stack.append(Path(path))
                                            continue
                                        f = {"id": hashlib.sha256((config["id"] + role + path).encode()).hexdigest()[:32], "root": root, "role": role, "path": path, "name": entry.name, "size": st.st_size, "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns, "identity": signature(st), "state": "pending", "reason": "Verificação pendente", "hash": None, "matches": [], "metadata_source": "lstat; ctime = alteração de metadados no Unix"}
                                        try:
                                            safe_stat(path, root)
                                        except (OSError, Blocked) as exc:
                                            f.update(state="blocked", reason=str(exc))
                                        job["files"].append(f)
                                        self._save_job(job, force=False)
                                    except OSError as exc:
                                        job["errors"].append({"path": path, "reason": str(exc)})
                        except OSError as exc:
                            job["errors"].append({"path": str(folder), "reason": str(exc)})
                        self._save_job(job, force=False)
            job["stage"] = "comparação SHA-256"
            self._save_job(job)
            refs = [f for f in job["files"] if f["role"] == "reference" and f["state"] != "blocked"]
            sizes = {f["size"] for f in job["files"] if f["role"] == "source" and f["state"] != "blocked"}
            needed = {f["size"] for f in refs} & sizes
            def progress(n):
                job["bytes_read"] += n
                now = time.monotonic()
                if now - progress.last > .25:
                    progress.last = now
                    self._save_job(job)
            progress.last = 0
            for f in job["files"]:
                if self.cancel.is_set():
                    raise InterruptedError()
                if f["state"] == "blocked" or f["size"] not in needed:
                    continue
                try:
                    key = hashlib.sha256((f["path"] + repr(f["identity"])).encode()).hexdigest()
                    cached = self.store.get("hash", key)
                    if signature(safe_stat(f["path"], f["root"])) != f["identity"]:
                        raise Blocked("Arquivo alterado desde o inventário.")
                    f["hash"] = cached["hash"] if cached else full_hash(f["path"], f["root"], f["identity"], self.cancel, progress)
                    f["hash_source"] = "cache de inventário" if cached else "SHA-256 completo em streaming"
                    self.store.put("hash", key, {"hash": f["hash"]})
                except InterruptedError:
                    raise
                except (OSError, Blocked) as exc:
                    f.update(state="blocked", reason=str(exc))
                self._save_job(job, force=False)
            matched_hashes = {}
            names = set()
            for ref in refs:
                names.add(ref["name"])
                if ref["hash"] and ref["state"] != "blocked":
                    matched_hashes.setdefault(ref["hash"], []).append(ref)
            incomplete = bool(job["errors"]) or any(r["role"] == "reference" and r["state"] == "blocked" for r in job["files"])
            for f in job["files"]:
                if f["state"] == "blocked":
                    continue
                if f["role"] == "reference":
                    f.update(state="reference", reason="Referência somente leitura")
                    continue
                f["matches"] = [r["id"] for r in matched_hashes.get(f["hash"], []) if r["identity"][:2] != f["identity"][:2]]
                if f["matches"]:
                    f.update(state="verified", reason="Conteúdo principal idêntico; metadados e fluxos especiais não verificados.")
                    f["group_id"] = hashlib.sha256((config["id"] + f["hash"]).encode()).hexdigest()[:32]
                elif f["name"] in names:
                    f.update(state="similar", reason="Mesmo nome, sem prova de igualdade.")
                else:
                    f.update(state="unmatched", reason="Nenhuma cópia idêntica encontrada no escopo examinado.")
                if incomplete:
                    if not f["matches"]:
                        f.update(state="pending", reason="Escopo incompleto: há erros ou referências bloqueadas.")
            job.update(status="completed", stage="concluído", finished_at=time.time())
        except InterruptedError:
            job.update(status="cancelled", stage="interrompido; retomar inicia nova varredura e revalida o cache")
        except Exception as exc:
            job.update(status="failed", stage="falha")
            job["errors"].append({"reason": str(exc)})
        finally:
            self._save_job(job)

    def plan(self, selections):
        with self.lock:
            job = self.store.get("job", "current")
            if not job or job["status"] != "completed":
                raise Blocked("Conclua o inventário antes de revisar.")
            current_config = self.store.get("config", "current")
            if current_config["id"] != job["config"]["id"]:
                raise Blocked("Configuração alterada; refaça inventário.")
            roots = validate_roots(current_config["source"], current_config["references"], self.store.directory)
            if roots["root_identities"] != current_config["root_identities"]:
                raise Blocked("Identidade de raiz alterada.")
            if not isinstance(selections, list) or not selections or len(selections) > 1000:
                raise Blocked("Selecione individualmente de 1 a 1000 arquivos.")
            by_id = {f["id"]: f for f in job["files"]}
            items, identities = [], set()
            for selection in selections:
                if not isinstance(selection, dict) or set(selection) != {"id", "exception"} or not isinstance(selection["exception"], bool):
                    raise Blocked("Seleção inválida. Envie apenas ID e decisão individual.")
                f = by_id.get(selection["id"])
                if not f or f["role"] != "source" or f["state"] in ("blocked", "pending"):
                    raise Blocked("ID inválido, referência ou arquivo tecnicamente bloqueado.")
                for operation in self.store.all("operation"):
                    if any(r["status"] in ("intent", "uncertain") and (r["path"] == f["path"] or r.get("identity", [])[:2] == f["identity"][:2]) for r in operation["results"]):
                        raise Blocked("Operação incerta nesta identidade/localização. Reconciliação manual obrigatória.")
                identity = tuple(f["identity"][:2])
                if identity in identities:
                    raise Blocked("Mesma identidade física selecionada mais de uma vez.")
                identities.add(identity)
                exception = selection["exception"]
                if not f["matches"] and not exception:
                    raise Blocked("Sem cópia: exige descarte excepcional individual explícito.")
                preserved = by_id[f["matches"][0]] if f["matches"] else None
                # Revisão também deve detectar mudanças; nunca autorizar pelo cache.
                digest = full_hash(f["path"], f["root"], f["identity"])
                if f["hash"] and digest != f["hash"]:
                    raise Blocked("Conteúdo alterado. Refaça inventário e revisão.")
                if preserved and full_hash(preserved["path"], preserved["root"], preserved["identity"]) != digest:
                    raise Blocked("Referência alterada. Refaça inventário e revisão.")
                f = {**f, "hash": digest}
                items.append({"source": copy.deepcopy(f), "preserved": copy.deepcopy(preserved), "exception": exception, "blocked_reason": None if self.adapter.supported else self.adapter.reason})
            plan = {"schema_version": 1, "id": opaque(), "job_id": job["id"], "config": job["config"], "created_at": time.time(), "items": items, "bytes": sum(i["source"]["size"] for i in items), "executable": self.adapter.supported}
            self.store.put("plan", plan["id"], plan)
            return plan

    def execute(self, plan_id):
        with self.lock:
            old = self.store.get("operation", plan_id)
            if old:
                return old
            if self.executing or self.worker and self.worker.is_alive():
                raise Blocked("Outra operação está em andamento.")
            plan = self.store.get("plan", plan_id)
            if not plan:
                raise Blocked("Plano desconhecido.")
            if not self.adapter.supported:
                raise Blocked(self.adapter.reason)
            job = self.store.get("job", "current")
            config = self.store.get("config", "current")
            if not job or job["id"] != plan["job_id"] or config["id"] != plan["config"]["id"]:
                raise Blocked("Plano invalidado. Faça uma nova revisão.")
            self.executing = True
            self.execution_cancel.clear()
            op = {"schema_version": 1, "id": plan_id, "started_at": time.time(), "status": "running", "results": []}
            self.store.put("operation", plan_id, op)
        try:
            for item in plan["items"]:
                f, ref = item["source"], item["preserved"]
                result = {"id": f["id"], "path": f["path"], "identity": f["identity"], "hash": f["hash"], "exception": item["exception"], "status": "intent"}
                op["results"].append(result)
                self.store.put("operation", plan_id, op)
                try:
                    if self.execution_cancel.is_set():
                        result.update(status="cancelled", reason="Cancelado antes da próxima operação.")
                    else:
                        roots = validate_roots(config["source"], config["references"], self.store.directory)
                        if roots["root_identities"] != config["root_identities"]:
                            raise Blocked("Raiz substituída.")
                        current_hash = full_hash(f["path"], f["root"], f["identity"])
                        if f["hash"] and current_hash != f["hash"]:
                            raise Blocked("Conteúdo de origem mudou; revise novo plano.")
                        if ref and full_hash(ref["path"], ref["root"], ref["identity"]) != current_hash:
                            raise Blocked("Cópia preservada mudou; revise novo plano.")
                        # O adaptador deve repetir a validação imediatamente
                        # antes da chamada nativa; a política aceita a janela
                        # concorrente depois de liberar os handles de leitura.
                        root_identities = dict(zip([config["source"], *config["references"]], config["root_identities"]))
                        native = self.adapter.recycle_guarded(
                            {**f, "hash": current_hash, "root_identity": root_identities[f["root"]]},
                            {**ref, "root_identity": root_identities[ref["root"]]} if ref else None)
                        if native.get("status") == "success" and native.get("native_evidence") and native.get("original_absent") and not os.path.lexists(f["path"]):
                            result.update(native)
                        elif native.get("status") in ("blocked", "cancelled", "failed"):
                            if os.path.lexists(f["path"]):
                                result.update(native)
                            else:
                                result.update(native, status="uncertain", reason="Origem ausente sem comprovação suficiente de reciclagem; reconcilie.")
                        else:
                            result.update(native, status="uncertain", reason=native.get("reason") or "Evidência nativa ou ausência do original insuficiente.")
                except (OSError, Blocked) as exc:
                    result.update(status="blocked", reason=str(exc))
                except Exception:
                    result.update(status="uncertain", reason="Falha do adaptador após intenção; reconcilie antes de tentar novamente.")
                self.store.put("operation", plan_id, op)
            op.update(status="completed", finished_at=time.time())
            self.store.put("operation", plan_id, op)
            return op
        finally:
            with self.lock:
                self.executing = False
