"""Abra com duplo clique onde Python está associado a .pyw."""
import sys

if sys.version_info < (3, 12):
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, "Instale Python 3.12 ou mais recente em python.org e abra novamente.", "Tidyup", 0x10)
    raise SystemExit(1)

from tidyup.desktop import main

main()
