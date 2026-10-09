"""Duplo clique: testar fluxo real somente com fixtures próprias."""
import ctypes
import os
import sys

if os.name != "nt" or sys.version_info < (3, 12):
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, "Requer Python 3.12 ou mais recente.", "Teste do fluxo Windows", 0x10)
    raise SystemExit(2)

from tidyup.desktop import default_data_dir
from tidyup.windows_flow_test import run

try:
    result, report = run(default_data_dir() / "native-test-reports")
    label = "PASSOU: fluxo do executor confirmado com fixtures." if result["status"] == "passed" else f"NÃO CONFIRMADO: {result['status']}."
    message = f"{label}\n\nNenhum arquivo pessoal foi selecionado.\nRelatório: {report}\n\nNão habilita limpeza normal nem testa interface/restauração."
    ctypes.windll.user32.MessageBoxW(None, message, "Teste do fluxo Windows", 0x40 if result["status"] == "passed" else 0x30)
except Exception as exc:
    ctypes.windll.user32.MessageBoxW(None, str(exc), "Falha no teste do fluxo", 0x10)
