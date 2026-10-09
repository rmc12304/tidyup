"""Gera um HTML autocontido e ZIP local sem dados operacionais."""
import hashlib
import json
import shutil
import tomllib
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent.parent


def build(destination=None):
    destination = Path(destination or ROOT / "dist")
    destination.mkdir(parents=True, exist_ok=True)
    static = ROOT / "tidyup" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="/style.css">', '<style>' + (static / "style.css").read_text() + '</style>')
    html = html.replace('<script src="/app.js" defer></script>', '')
    html = html.replace('</body>', '<script>' + (static / "app.js").read_text().replace('</script', '<\\/script') + '</script></body>')
    html = html.replace('class="brand" href="/"', 'class="brand" href="#"')
    output = destination / "Tidyup.html"
    output.write_text(html, encoding="utf-8")
    allowed = ["tidyup", "docs", "examples", "tests", "tools"]
    root_files = ["Abrir Tidyup.cmd", "Abrir Tidyup.pyw", "Testar Lixeira.cmd", "Testar Lixeira.pyw", "Testar Fluxo Windows.cmd", "Testar Fluxo Windows.pyw", "README.md", "AGENTS.md", "CHANGELOG.md", "pyproject.toml", "requirements.lock", "requirements-browser.lock", ".gitignore"]
    paths = [ROOT / name for name in root_files]
    for name in allowed:
        paths.extend(p for p in (ROOT / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo"))
    archive = destination / "tidyup-local.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(output, "tidyup-local/Tidyup.html")
        for path in sorted(paths):
            bundle.write(path, "tidyup-local/" + path.relative_to(ROOT).as_posix())
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (output, archive)}
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    if not all(part.isdigit() for part in version.split(".")) or len(version.split(".")) != 3:
        raise ValueError("Versão do pacote deve ser major.minor.patch.")
    versioned_archive = destination / f"tidyup-local-{version}.zip"
    shutil.copyfile(archive, versioned_archive)
    hashes[versioned_archive.name] = hashes[archive.name]
    (destination / "SHA256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return output, archive


if __name__ == "__main__":
    for path in build():
        print(path)
