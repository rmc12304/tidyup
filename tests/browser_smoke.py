"""Teste opcional: requer Playwright e Chromium já instalados. Só fixtures."""
import json
import shutil
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from tidyup.core import Engine
from tidyup.server import create_server
from tidyup.storage import Store
from tools.build_local import build


def main():
    with tempfile.TemporaryDirectory(prefix="tidyup-browser-") as tmp:
        base = Path(tmp)
        source, reference = base / "source", base / "reference"
        source.mkdir(); reference.mkdir()
        for i in range(105):
            (source / f"arquivo {i:03}.txt").write_bytes(f"fixture {i}".encode())
            (reference / f"copia {i:03}.txt").write_bytes(f"fixture {i}".encode())
        (source / '<img src=x onerror="window.pwned=1">').write_bytes(b"special")
        (reference / "special").write_bytes(b"special")
        (source / "sem copia.txt").write_bytes(b"sem referencia")
        store = Store(base / "data")
        engine = Engine(store)
        server = create_server(engine, 0)
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        try:
            with sync_playwright() as p:
                chromium = shutil.which("chromium")
                browser = p.chromium.launch(headless=True, **({"executable_path": chromium} if chromium else {}))
                page = browser.new_page(viewport={"width": 390, "height": 844})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}")
                page.locator("#source").fill(str(source))
                page.locator("#references").fill(str(reference))
                page.get_by_role("button", name="Validar raízes").click()
                page.locator("#scan").click()
                expect(page.locator("#progress")).to_contain_text("concluído", timeout=30000)
                assert page.locator("article.card").count() == 50
                assert '<img src=x onerror="window.pwned=1">' in page.locator("#items").inner_text()
                assert page.locator("article.card img").count() == 0
                assert page.evaluate("window.pwned") is None
                assert page.locator("#selected-count").inner_text() == "0 arquivos selecionados"
                checkbox = page.locator("article.card input[type=checkbox]").first
                checkbox.focus()
                page.keyboard.press("Space")
                assert page.locator("#selected-count").inner_text() == "1 arquivos selecionados"
                page.locator("#review").click()
                expect(page.locator("dialog")).to_be_visible()
                assert page.locator("#execute").is_disabled()
                assert page.locator("#plan-items .plan-item").count() == 1
                page.keyboard.press("Escape")
                expect(page.locator("dialog")).not_to_be_visible()
                page.locator("#next").click()
                expect(page.locator("#page")).to_contain_text("51–100")
                assert page.locator("#selected-count").inner_text() == "1 arquivos selecionados"
                page.locator("#next").click()
                expect(page.locator("#page")).to_contain_text("101–107")
                assert page.locator("article.card").count() == 7
                assert page.locator("#next").is_disabled()
                assert page.evaluate("window.pwned") is None
                assert page.locator("article.card img").count() == 0
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.locator("#review").click()
                expect(page.locator("dialog")).to_be_visible()
                page.locator("#back").click()
                page.set_viewport_size({"width": 1280, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                assert not errors, errors
                screenshot = Path("/tmp/tidyup-browser.png")
                page.screenshot(path=str(screenshot), full_page=True)
                page.locator("#native-diagnostics").click()
                expect(page.locator("#native-status")).to_contain_text("Windows")
                page.locator("#shutdown").click()
                expect(page.locator("#capability")).to_contain_text("Aplicativo encerrado")
                expect(page.locator("#shutdown")).to_be_disabled()
                standalone, _ = build(base / "package")
                offline = browser.new_page(viewport={"width": 390, "height": 844})
                outbound = []
                offline.on("request", lambda request: outbound.append(request.url) if request.url.startswith(("http:", "https:")) else None)
                offline_file_navigation = "passed"
                try:
                    offline.goto(standalone.as_uri())
                except Exception as exc:
                    if "ERR_BLOCKED_BY_ADMINISTRATOR" not in str(exc):
                        raise
                    offline_file_navigation = "blocked_by_browser_admin_policy; offline render tested with simulated file protocol"
                    # Não alterar a política do navegador. Testar o HTML em
                    # memória, simulando só a seleção do ramo offline.
                    offline.close()
                    offline = browser.new_page(viewport={"width": 390, "height": 844})
                    offline.on("request", lambda request: outbound.append(request.url) if request.url.startswith(("http:", "https:")) else None)
                    offline.set_content(standalone.read_text().replace('location.protocol===', '"file:"==='))
                expect(offline.locator("#capability")).to_contain_text("Você abriu o HTML local")
                expect(offline.locator("#source")).to_be_disabled()
                expect(offline.locator("#native-diagnostics")).to_be_disabled()
                assert not outbound, outbound
                print(json.dumps({"status": "passed", "fixtures": 107, "viewports": ["390x844", "1280x900"], "checks": ["keyboard selection", "dialog escape/focus", "pagination", "persistent selection", "XSS escaping", "native action disabled", "no horizontal overflow", "shutdown UI", "offline controls disabled", "offline no network requests"], "offline_file_navigation": offline_file_navigation, "screenshot": str(screenshot)}))
                browser.close()
        finally:
            server.shutdown(); server.server_close(); worker.join()
            if engine.worker:
                engine.worker.join()
            store.close()


if __name__ == "__main__":
    main()
