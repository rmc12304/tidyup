"""Contrato para adaptadores nativos. Sem fallback destrutivo."""
from typing import Protocol
import os
from pathlib import Path
import tempfile

from .filesystem import Blocked, full_hash


class TrashAdapter(Protocol):
    supported: bool
    reason: str

    def recycle_guarded(self, source: dict, preserved: dict | None) -> dict:
        """Revalidar identidade/localização/hash de AMBOS os itens imediatamente
        antes da reciclagem. A política do usuário aceita a janela após liberar
        handles. Retornar evidência nativa por item e original_absent.
        Nunca excluir permanentemente. Sem prova de reciclagem, bloquear/incerto.
        """
        ...


class UnavailableTrash:
    supported = False
    reason = "Lixeira indisponível: não há adaptador nativo validado nesta versão, inclusive no Windows."

    def recycle_guarded(self, source, preserved):
        return {"status": "blocked", "reason": self.reason}


class WindowsTrash(UnavailableTrash):
    reason = "Limpeza normal bloqueada até validar o adaptador completo no Windows. Use Testar Fluxo Windows para fixtures; diagnóstico COM não habilita limpeza."
    cancel_event = None

    def bind_cancel(self, event):
        self.cancel_event = event

    def recycle_guarded(self, source, preserved):
        if not self.supported:
            return {"status": "blocked", "reason": self.reason}
        from .windows_recycle import perform_recycle, classify
        evidence = {}
        entered_native = False
        try:
            path = Path(source["path"])
            expected = source["hash"]
            if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
                raise Blocked("Hash completo de origem obrigatório.")

            def verify(shell_source):
                if self.cancel_event and self.cancel_event.is_set():
                    raise InterruptedError("Cancelado antes da movimentação nativa.")
                self.check_scope(source, preserved)
                if not shell_source or Path(shell_source).resolve() != path:
                    raise Blocked("Item Shell diferente da origem revisada.")
                if full_hash(path, source["root"], source["identity"], cancel=self.cancel_event) != expected:
                    raise Blocked("Origem alterada antes da movimentação.")
                if preserved and full_hash(preserved["path"], preserved["root"], preserved["identity"], cancel=self.cancel_event) != expected:
                    raise Blocked("Referência alterada antes da movimentação.")

            verify(str(path))
            entered_native = True
            native = perform_recycle(path, verify)
            absent = not os.path.lexists(path)
            evidence.update(native=native, original_absent=absent)
            recycled_hash = None
            for event in native.get("events", []):
                if event.get("stage") == "post_delete" and event.get("recycled_path"):
                    recycled = Path(event["recycled_path"])
                    try:
                        recycled_hash = full_hash(recycled, recycled.parent)
                    except (OSError, ValueError) as exc:
                        evidence["recycled_read_error"] = str(exc)
            # Não usar cancelamento para omitir provas de um item já movimentado.
            reference_hash = full_hash(preserved["path"], preserved["root"], preserved["identity"]) if preserved else expected
            evidence.update(recycled_sha256=recycled_hash, reference_sha256=reference_hash if preserved else None)
            outcome = classify(native, absent, recycled_hash, expected, reference_hash)
            return {"status": "success" if outcome == "passed" else outcome,
                    "original_absent": absent, "native_evidence": evidence,
                    "reason": "Resultado por item: callbacks, ausência e hashes conferidos."}
        except Exception as exc:
            # Após entrar na camada COM, qualquer exceção exige reconciliação;
            # não classificá-la como bloqueio seguro nem repetir automaticamente.
            return {"status": "uncertain" if entered_native else ("cancelled" if isinstance(exc, InterruptedError) else "blocked"),
                    "reason": str(exc), "native_evidence": evidence}

    def check_scope(self, source, preserved):
        for item in (source, preserved):
            if item is None:
                continue
            root, path = Path(item["root"]), Path(item["path"])
            if not root.is_absolute() or not path.is_absolute() or not path.is_relative_to(root):
                raise Blocked("Item fora da raiz revisada.")
            if self.directory_identity(root) != item.get("root_identity"):
                raise Blocked("Identidade de raiz alterada antes da chamada nativa.")
        if preserved:
            origin_root, reference_root = Path(source["root"]), Path(preserved["root"])
            if origin_root.is_relative_to(reference_root) or reference_root.is_relative_to(origin_root):
                raise Blocked("Origem e referência devem estar em raízes separadas.")
            if source["identity"][:2] == preserved["identity"][:2]:
                raise Blocked("Origem e referência compartilham identidade.")

    @staticmethod
    def directory_identity(path):
        st = path.lstat()
        if not path.is_dir() or path.resolve() != path or getattr(st, "st_file_attributes", 0) & 0x400:
            raise Blocked("Raiz redirecionada.")
        return [st.st_dev, st.st_ino]

    def diagnostics(self):
        from .windows import probe_ifileoperation
        return probe_ifileoperation()


class WindowsFixtureTrash(WindowsTrash):
    """Mesmo adaptador, habilitado apenas no runner de fixtures; sem rota/API.

    O runner cria uma raiz nova em TEMP e injeta este adaptador no Engine.
    Nada habilita o adaptador padrão ou aceita raízes pessoais.
    """
    supported = True
    reason = "Teste do fluxo Windows limitado a fixtures próprias."

    def __init__(self, fixture_root):
        self.fixture_root = Path(fixture_root)
        if (self.fixture_root.resolve() != self.fixture_root
                or self.fixture_root.parent != Path(tempfile.gettempdir()).resolve()
                or not self.fixture_root.name.startswith("tidyup-windows-flow-")):
            raise Blocked("Adaptador de teste requer fixture própria em TEMP.")
        self.roots = {role: self.fixture_root / role for role in ("source", "reference")}
        self.identities = {role: self.directory_identity(path) for role, path in self.roots.items()}

    def check_scope(self, source, preserved):
        super().check_scope(source, preserved)
        for role, item in (("source", source), ("reference", preserved)):
            root = self.roots[role]
            if self.directory_identity(root) != self.identities[role]:
                raise Blocked("Raiz de fixture substituída.")
            if item is not None and (Path(item["root"]) != root or not Path(item["path"]).is_relative_to(root)):
                raise Blocked("Item fora da fixture autorizada.")


def default_adapter():
    return WindowsTrash() if os.name == "nt" else UnavailableTrash()
