"""Win32 experimental: leitura protegida e diagnóstico COM, sem exclusão."""
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import os
from pathlib import PureWindowsPath
import uuid


class AttributeTag(ctypes.Structure):
    _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]


class GUID(ctypes.Structure):
    _fields_ = [("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16), ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


def extended_path(path):
    p = PureWindowsPath(path)
    if not p.is_absolute() or str(p).startswith("\\\\") or any(part in (".", "..") for part in p.parts):
        raise ValueError("Só caminhos absolutos de volumes Windows locais são aceitos; UNC/redes bloqueados.")
    if any(":" in part for part in p.parts[1:]):
        raise ValueError("Fluxos alternativos não são aceitos.")
    return "\\\\?\\" + str(p)


class WindowsAPI:
    def __init__(self):
        if os.name != "nt":
            raise OSError("As APIs Win32 requerem Python nativo Windows, não WSL.")
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.create = self.kernel.CreateFileW
        self.create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self.create.restype = wintypes.HANDLE
        self.close = self.kernel.CloseHandle
        self.close.argtypes = [wintypes.HANDLE]
        self.close.restype = wintypes.BOOL
        self.info = self.kernel.GetFileInformationByHandleEx
        self.info.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.info.restype = wintypes.BOOL
        self.drive_type = self.kernel.GetDriveTypeW
        self.drive_type.argtypes = [wintypes.LPCWSTR]
        self.drive_type.restype = wintypes.UINT

    def open(self, path, directory):
        path = PureWindowsPath(path)
        if self.drive_type(path.anchor) not in (2, 3):
            raise ValueError("Volume de rede/não local bloqueado.")
        access = 0x80 if directory else 0x80000000
        sharing = 3 if directory else 1  # READ|WRITE / READ; nunca SHARE_DELETE
        flags = 0x00200000 | 0x00100000  # OPEN_REPARSE_POINT | OPEN_NO_RECALL
        flags |= 0x02000000 if directory else 0x08000000
        handle = self.create(extended_path(path), access, sharing, None, 3, flags, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            attributes = AttributeTag()
            if not self.info(handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)):
                raise ctypes.WinError(ctypes.get_last_error())
            if attributes.attributes & (0x400 | 0x1000 | 0x40000 | 0x400000):
                raise ValueError(f"Reparse/offline/sob demanda bloqueado; tag=0x{attributes.tag:08x}. Não hidratar.")
            if bool(attributes.attributes & 0x10) != directory:
                raise ValueError("Tipo do objeto mudou durante abertura.")
            return handle
        except Exception:
            self.close(handle)
            raise


@contextmanager
def directory_guard(path, api=None):
    api = api or WindowsAPI()
    path = PureWindowsPath(path)
    extended_path(path)
    handles = []
    try:
        current = PureWindowsPath(path.anchor)
        handles.append(api.open(current, True))
        for component in path.parts[1:]:
            current /= component
            handles.append(api.open(current, True))
        yield
    finally:
        for handle in reversed(handles):
            api.close(handle)


@contextmanager
def guarded_fd(path):
    import msvcrt
    api = WindowsAPI()
    path = PureWindowsPath(path)
    with directory_guard(path.parent, api):
        handle = api.open(path, False)
        try:
            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        except Exception:
            api.close(handle)
            raise
        try:
            if os.fstat(fd).st_nlink != 1:
                raise ValueError("Hard link bloqueado.")
            yield fd
        finally:
            os.close(fd)


def probe_ifileoperation():
    """COM STA e flags; nunca enfileirar DeleteItem/PerformOperations."""
    if os.name != "nt":
        return {"available": False, "reason": "Requer Windows nativo."}
    ole = ctypes.WinDLL("ole32")
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole.CoInitializeEx.restype = ctypes.c_long
    result = ole.CoInitializeEx(None, 2)
    if result < 0:
        return {"available": False, "reason": f"CoInitializeEx HRESULT 0x{result & 0xffffffff:08x}"}
    interface = ctypes.c_void_p()
    try:
        clsid = GUID.parse("3ad05575-8857-4850-9277-11b85bdb8e09")
        iid = GUID.parse("947aab5f-0a5c-4c13-b4d6-4bf7836fc9f8")
        ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        ole.CoCreateInstance.restype = ctypes.c_long
        hr = ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(interface))
        if hr < 0:
            return {"available": False, "reason": f"IFileOperation HRESULT 0x{hr & 0xffffffff:08x}"}
        table = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        set_flags = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.DWORD)(table[5])
        flags = 0x00080000 | 0x00100000 | 0x0400 | 0x1000
        hr = set_flags(interface, flags)
        return {"available": hr >= 0, "flags": flags, "hresult": f"0x{hr & 0xffffffff:08x}", "operational": False, "reason": "COM somente para diagnóstico; nenhuma exclusão agendada. Proteção concorrente não estabelecida."}
    finally:
        if interface.value:
            table = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(table[2])(interface)
        ole.CoUninitialize()
