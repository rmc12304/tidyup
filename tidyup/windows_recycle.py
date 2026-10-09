"""IFileOperation compartilhado pelos testes e pelo adaptador Windows. Sem fallback."""
import ctypes
import os
from pathlib import Path
import sys
import uuid

from .windows import GUID

HRESULT = ctypes.c_int32
DWORD = ctypes.c_uint32
PTR = ctypes.c_void_p
RECYCLE_FLAGS = 0x00080000 | 0x00100000 | 0x0400 | 0x1000 | 0x0010
SINK_IID = "04b0f1a7-9490-44bc-96e1-4296a31252e2"


def hex_hr(value):
    return f"0x{value & 0xffffffff:08x}"


def com_method(pointer, slot, *arguments, result=HRESULT):
    table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(PTR))).contents
    return ctypes.WINFUNCTYPE(result, PTR, *arguments)(table[slot])


def check_hr(value, operation):
    if value < 0:
        raise OSError(f"{operation}: HRESULT {hex_hr(value)}")


def shell_path(pointer, ole):
    result = PTR()
    check_hr(com_method(pointer, 5, DWORD, ctypes.POINTER(PTR))(pointer, 0x80058000, ctypes.byref(result)), "GetDisplayName")
    try:
        return ctypes.wstring_at(result) if result.value else None
    finally:
        if result.value:
            ole.CoTaskMemFree(result)


class ProgressSink:
    """Vtable IFileOperationProgressSink; vida útil mantida até Release COM."""
    def __init__(self, verify, ole):
        self.events = []
        self.references = 1
        self.verify = verify
        self.ole = ole
        # Ordem e tipos do SDK: IUnknown + IFileOperationProgressSink.
        signatures = [
            (HRESULT, (PTR, PTR, ctypes.POINTER(PTR))),
            (DWORD, (PTR,)), (DWORD, (PTR,)),
            (HRESULT, (PTR,)), (HRESULT, (PTR, HRESULT)),
            (HRESULT, (PTR, DWORD, PTR, ctypes.c_wchar_p)),
            (HRESULT, (PTR, DWORD, PTR, ctypes.c_wchar_p, HRESULT, PTR)),
            (HRESULT, (PTR, DWORD, PTR, PTR, ctypes.c_wchar_p)),
            (HRESULT, (PTR, DWORD, PTR, PTR, ctypes.c_wchar_p, HRESULT, PTR)),
            (HRESULT, (PTR, DWORD, PTR, PTR, ctypes.c_wchar_p)),
            (HRESULT, (PTR, DWORD, PTR, PTR, ctypes.c_wchar_p, HRESULT, PTR)),
            (HRESULT, (PTR, DWORD, PTR)),
            (HRESULT, (PTR, DWORD, PTR, HRESULT, PTR)),
            (HRESULT, (PTR, DWORD, PTR, ctypes.c_wchar_p)),
            (HRESULT, (PTR, DWORD, PTR, ctypes.c_wchar_p, ctypes.c_wchar_p, DWORD, HRESULT, PTR)),
            (HRESULT, (PTR, DWORD, DWORD)),
            (HRESULT, (PTR,)), (HRESULT, (PTR,)), (HRESULT, (PTR,)),
        ]
        handlers = [self.query, self.addref, self.release, self.ok, self.ok,
                    self.deny, self.ok, self.deny, self.ok, self.deny, self.ok,
                    self.pre_delete, self.post_delete, self.deny, self.ok,
                    self.ok, self.ok, self.ok, self.ok]
        self.callbacks = [ctypes.WINFUNCTYPE(ret, *args)(handler) for (ret, args), handler in zip(signatures, handlers)]
        self.table = (PTR * len(self.callbacks))(*[ctypes.cast(callback, PTR).value for callback in self.callbacks])
        class Object(ctypes.Structure):
            _fields_ = [("vtable", ctypes.POINTER(PTR))]
        self.object = Object(ctypes.cast(self.table, ctypes.POINTER(PTR)))
        self.pointer = ctypes.cast(ctypes.pointer(self.object), PTR)

    def query(self, _this, iid, result):
        value = ctypes.string_at(iid, 16)
        if value in (uuid.UUID(SINK_IID).bytes_le, uuid.UUID("00000000-0000-0000-c000-000000000046").bytes_le):
            result[0] = self.pointer.value
            self.references += 1
            return 0
        result[0] = None
        return -2147467262  # E_NOINTERFACE

    def addref(self, *_args):
        self.references += 1
        return self.references

    def release(self, *_args):
        self.references = max(0, self.references - 1)
        return self.references

    def ok(self, *_args):
        return 0

    def deny(self, *_args):
        return -2147024891  # E_ACCESSDENIED: não autorizar outros tipos de operação.

    def pre_delete(self, _this, flags, item):
        try:
            self.verify(shell_path(item, self.ole))
            self.events.append({"stage": "pre_delete", "flags": flags, "verified": True})
            return 0
        except Exception as exc:
            self.events.append({"stage": "pre_delete", "verified": False, "reason": str(exc)})
            return -2147467260  # E_ABORT

    def post_delete(self, _this, flags, item, hr, recycled):
        event = {"stage": "post_delete", "flags": flags, "hresult": hex_hr(hr), "native_success": hr >= 0, "recycle_item_returned": bool(recycled)}
        try:
            if recycled:
                event["recycled_path"] = shell_path(recycled, self.ole)
        except Exception as exc:
            event["path_error"] = str(exc)
        self.events.append(event)
        return 0


def perform_recycle(source, verify):
    """Uma operação por item; verify bloqueia escopo/hash antes e no callback.

    Somente adaptadores internos chamam esta função, nunca caminhos da API.
    """
    if os.name != "nt" or sys.getwindowsversion().major < 6 or (sys.getwindowsversion().major == 6 and sys.getwindowsversion().minor < 2):
        raise OSError("Requer Windows 8 ou mais recente para RECYCLEONDELETE.")
    source = Path(source)
    ole = ctypes.WinDLL("ole32")
    shell = ctypes.WinDLL("shell32")
    ole.CoInitializeEx.argtypes = [PTR, DWORD]
    ole.CoInitializeEx.restype = HRESULT
    ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), PTR, DWORD, ctypes.POINTER(GUID), ctypes.POINTER(PTR)]
    ole.CoCreateInstance.restype = HRESULT
    ole.CoTaskMemFree.argtypes = [PTR]
    ole.CoTaskMemFree.restype = None
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    shell.SHCreateItemFromParsingName.argtypes = [ctypes.c_wchar_p, PTR, ctypes.POINTER(GUID), ctypes.POINTER(PTR)]
    shell.SHCreateItemFromParsingName.restype = HRESULT
    check_hr(ole.CoInitializeEx(None, 2), "CoInitializeEx STA")
    operation, item = PTR(), PTR()
    sink = None
    try:
        clsid = GUID.parse("3ad05575-8857-4850-9277-11b85bdb8e09")
        iid = GUID.parse("947aab5f-0a5c-4c13-b4d6-4bf7836fc9f8")
        check_hr(ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(operation)), "CoCreateInstance IFileOperation")
        check_hr(com_method(operation, 5, DWORD)(operation, RECYCLE_FLAGS), "SetOperationFlags")
        item_iid = GUID.parse("43826d1e-e718-42ee-bc55-a1e261c37bfe")
        check_hr(shell.SHCreateItemFromParsingName(str(source), None, ctypes.byref(item_iid), ctypes.byref(item)), "SHCreateItemFromParsingName")
        sink = ProgressSink(verify, ole)
        verify(str(source))
        check_hr(com_method(operation, 18, PTR, PTR)(operation, item, sink.pointer), "DeleteItem (agendamento)")
        performed = com_method(operation, 21)(operation)
        aborted = ctypes.c_int32()
        aborted_hr = com_method(operation, 22, ctypes.POINTER(ctypes.c_int32))(operation, ctypes.byref(aborted))
        return {"perform_hresult": hex_hr(performed), "perform_success": performed >= 0,
                "aborted_hresult": hex_hr(aborted_hr), "aborted_query_success": aborted_hr >= 0,
                "aborted": bool(aborted.value), "events": sink.events, "flags": RECYCLE_FLAGS}
    finally:
        for pointer in (item, operation):
            if pointer.value:
                com_method(pointer, 2, result=DWORD)(pointer)
        ole.CoUninitialize()


def classify(native, original_absent, recycled_hash, expected_hash, reference_hash):
    """Sucesso exige callback de reciclagem e hash do item reciclado, não só ausência."""
    posts = [event for event in native.get("events", []) if event.get("stage") == "post_delete"]
    pres = [event for event in native.get("events", []) if event.get("stage") == "pre_delete"]
    success = len(posts) == 1 and posts[0].get("native_success") and posts[0].get("recycle_item_returned")
    if (native.get("perform_success") and native.get("aborted_query_success") and not native.get("aborted")
            and len(pres) == 1 and pres[0].get("verified") and success and original_absent and recycled_hash == expected_hash == reference_hash):
        return "passed"
    if original_absent:
        return "uncertain"
    return "cancelled" if native.get("aborted") else "failed"
