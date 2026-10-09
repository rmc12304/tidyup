"""Leitura em streaming. Nenhuma função de exclusão ou movimentação aqui."""
import hashlib
import os
import stat
from contextlib import contextmanager
from pathlib import Path


class Blocked(ValueError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details


def anchored_open(path, flags):
    """Linux/POSIX: abrir cada ancestral por descritor sem seguir links.

    A enumeração e o hash falham fechados onde dir_fd/O_NOFOLLOW não existem.
    Um adaptador Windows deve fornecer a proteção equivalente com handles.
    """
    if os.open not in os.supports_dir_fd or not hasattr(os, "O_NOFOLLOW"):
        raise Blocked("Leitura ancorada não suportada nesta plataforma; adaptador de handles necessário.")
    path = Path(path)
    if not path.is_absolute():
        raise Blocked("Caminho absoluto obrigatório.")
    parts = path.parts[1:]
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open(path.anchor, directory_flags)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=parent)
            os.close(parent)
            parent = next_fd
        return os.open(parts[-1], flags | os.O_NOFOLLOW, dir_fd=parent) if parts else os.dup(parent)
    finally:
        os.close(parent)


def signature(st):
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_nlink]


def descriptor_path_signature(st, *, windows=None):
    """Comparar as mesmas datas entre path stat e fstat no Windows.

    CPython Windows mantém ctime de stat/lstat como criação por compatibilidade,
    enquanto fstat pode trazer ChangeTime. Para a comparação cruzada, usar a
    criação explícita do descritor; fstat antes/depois continua comparando o
    ChangeTime bruto para detectar mudanças durante a leitura.
    """
    result = signature(st)
    if (os.name == "nt" if windows is None else windows):
        birthtime = getattr(st, "st_birthtime_ns", None)
        if birthtime is not None:
            result[4] = birthtime
    return result


@contextmanager
def directory_entries(folder):
    if os.name == "nt":
        from .windows import directory_guard, extended_path
        with directory_guard(folder), os.scandir(extended_path(folder)) as entries:
            yield sorted(entries, key=lambda entry: entry.name)
    else:
        fd = anchored_open(folder, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with os.scandir(fd) as entries:
                yield sorted(entries, key=lambda entry: entry.name)
        finally:
            os.close(fd)


@contextmanager
def readable_fd(path):
    if os.name == "nt":
        from .windows import guarded_fd
        with guarded_fd(path) as fd:
            yield fd
    else:
        fd = anchored_open(path, os.O_RDONLY)
        try:
            yield fd
        finally:
            os.close(fd)


def safe_stat(path, root):
    path, root = Path(path), Path(root)
    if not path.is_relative_to(root):
        raise Blocked("Caminho fora da raiz autorizada.")
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        st = current.lstat()
        if stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & 0x400:
            raise Blocked("Link, junction ou reparse point: leitura e operação bloqueadas.")
    st = path.lstat()
    if path.resolve() != path or root.resolve() != root:
        raise Blocked("A localização canônica mudou.")
    if not stat.S_ISREG(st.st_mode):
        raise Blocked("Somente arquivos regulares são aceitos.")
    if st.st_nlink != 1:
        raise Blocked("Hard link: identidade compartilhada não elegível.")
    if getattr(st, "st_file_attributes", 0) & (0x1000 | 0x40000 | 0x400000):
        raise Blocked("Arquivo offline/sob demanda: hidratação não autorizada.")
    return st


def full_hash(path, root, expected=None, cancel=None, progress=None):
    before = safe_stat(path, root)
    if expected is not None and signature(before) != expected:
        raise Blocked("Arquivo alterado ou substituído desde o inventário.")
    with readable_fd(path) as fd:
        descriptor_before = os.fstat(fd)
        if descriptor_path_signature(descriptor_before) != signature(before):
            raise Blocked("Arquivo substituído durante a abertura.", {
                "phase": "open", "path_signature": signature(before),
                "descriptor_signature": signature(descriptor_before),
                "descriptor_path_signature": descriptor_path_signature(descriptor_before)})
        digest = hashlib.sha256()
        with os.fdopen(fd, "rb", closefd=False) as stream:
            while True:
                if cancel and cancel.is_set():
                    raise InterruptedError("Inventário cancelado; retome para revalidar.")
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                if progress:
                    progress(len(chunk))
        descriptor_after = os.fstat(fd)
        path_after = safe_stat(path, root)
        if signature(descriptor_after) != signature(descriptor_before) or signature(path_after) != signature(before):
            raise Blocked("Arquivo alterado durante a leitura.", {
                "phase": "read", "descriptor_before": signature(descriptor_before),
                "descriptor_after": signature(descriptor_after), "path_before": signature(before),
                "path_after": signature(path_after)})
        return digest.hexdigest()


def validate_roots(source, references, data_dir):
    if not isinstance(source, str) or not isinstance(references, list) or not references or not all(isinstance(r, str) for r in references):
        raise Blocked("Escolha uma origem e pelo menos uma referência.")
    chosen = [source, *references]
    roots = []
    for raw in chosen:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            raise Blocked("Use caminhos absolutos.")
        canonical = p.resolve(strict=True)
        if canonical != Path(os.path.abspath(p)):
            raise Blocked("Raízes com redirecionamentos não são aceitas; escolha o caminho físico.")
        if not canonical.is_dir():
            raise Blocked("A raiz precisa ser uma pasta existente.")
        if getattr(canonical.stat(), "st_file_attributes", 0) & 0x400:
            raise Blocked("Raiz reparse não suportada.")
        roots.append(canonical)
    all_roots = [*roots, Path(data_dir).resolve()]
    identities = set()
    for i, root in enumerate(all_roots):
        st = root.stat()
        identity = (st.st_dev, st.st_ino)
        if identity in identities:
            raise Blocked("Raízes compartilham a mesma identidade física.")
        identities.add(identity)
        for other in all_roots[:i]:
            if root.is_relative_to(other) or other.is_relative_to(root):
                raise Blocked("Origem, referências e DATA_DIR não podem se sobrepor.")
    return {"source": str(roots[0]), "references": [str(r) for r in roots[1:]], "root_identities": [[r.stat().st_dev, r.stat().st_ino] for r in roots]}
