"""Duplo clique é o opt-in explícito: só criar/reciclar uma fixture própria."""
import ctypes
import os
import sys

if os.name != "nt" or sys.version_info < (3, 12):
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, "Requer Python 3.12 ou mais recente.", "Teste da Lixeira", 0x10)
    raise SystemExit(2)

from tidyup.desktop import default_data_dir
from tidyup.windows_recycle_test import run

try:
    result, report = run(default_data_dir() / "native-test-reports")
    label = "PASSOU: reciclagem nativa comprovada da fixture." if result["status"] == "passed" else f"NÃO CONFIRMADO: {result['status']}."
    detail = f"\nVerificação do conteúdo reciclado: {result['recycled_read_error']}" if result.get("recycled_read_error") else ""
    message = f"{label}{detail}\n\nNenhum arquivo pessoal foi selecionado.\nRelatório: {report}\n\nO teste não habilita a limpeza do aplicativo nem testa restauração."
    ctypes.windll.user32.MessageBoxW(None, message, "Teste real da Lixeira", 0x40 if result["status"] == "passed" else 0x30)
except Exception as exc:
    ctypes.windll.user32.MessageBoxW(None, str(exc), "Falha no teste da Lixeira", 0x10)
