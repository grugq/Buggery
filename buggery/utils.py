
import os
import win32api
import win32con

from ctypes import *
import comtypes.server
import comtypes.server.connectionpoints
from comtypes import HRESULT, COMError
from comtypes.client import CreateObject, GetEvents, ShowEvents
from comtypes.hresult import S_OK
from comtypes.automation import IID


try:
    from comtypes.gen import DbgEng
except ImportError:
    import comtypes

    # XXX HACKHACKHACK this makes me feel dirty. And not in a good way.
    tlb_file = os.path.join(os.path.dirname(__file__), "DbgEng.tlb")
    comtypes.client.GetModule(tlb_file)

    from comtypes.gen import DbgEng

DBGENG_DLL = None
DBGHELP_DLL = None


def module_from_tlb(tlb_file):
    comtypes.client.GetModule(tlb_file)

def find_dbg_eng_path():
    def check_registery():
        hkey = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, "Software\\Microsoft\\DebuggingTools")
        val, type = win32api.RegQueryValueEx(hkey, "WinDbg")
        return val

    def check_common_locations():
        # Lets try a few common places before failing.
        pgPaths = [
                "c:\\",
                os.environ["SystemDrive"]+"\\",
                os.environ["ProgramFiles"],
                ]
        if "ProgramW6432" in os.environ:
                pgPaths.append(os.environ["ProgramW6432"])
        if "ProgramFiles(x86)" in os.environ:
                pgPaths.append(os.environ["ProgramFiles(x86)"])

        dbgPaths = [
                "Debuggers",
                "Debugger",
                "Debugging Tools for Windows",
                "Debugging Tools for Windows (x64)",
                "Debugging Tools for Windows (x86)",
                ]

        for p in pgPaths:
            for d in dbgPaths:
                testPath = os.path.join(p,d)
                if os.path.exists(testPath):
                    return testPath

    try:
        dll_path = check_registery()
    except:
        dll_path = check_common_locations()

    if dll_path is None:
        raise DebuggerException("Failed to locate Microsoft Debugging Tools in the registry. Please make sure its installed")

    return dll_path

def load_dbgeng_dlls():
    global DBGENG_DLL, DBGHELP_DLL

    dllpath = find_dbg_eng_path()

    DBGHELP_DLL = windll.LoadLibrary(os.path.join(dllpath, "dbghelp.dll"))
    DBGENG_DLL = windll.LoadLibrary(os.path.join(dllpath, "dbgeng.dll"))

def create_idebug_client():
    #idebug_guid = comtypes.GUID("{27fe5639-8407-4f47-8364-ee118fb08ac8}")
    #return comtypes.client.CreateObject(idebug_guid, comtypes.CLSCTX_INPROC_SERVER, interface=DbgEng.IDebugClient)

    def debug_create(dbgeng_dll):
        # DebugCreate() prototype
        debug_create_prototype = WINFUNCTYPE(HRESULT, POINTER(IID), POINTER(POINTER(DbgEng.IDebugClient)))
        debug_create_func = debug_create_prototype(("DebugCreate", dbgeng_dll))

        # call DebugCreate()
        idebug_client = POINTER(DbgEng.IDebugClient)()
        idebug_client_ptr = POINTER(POINTER(DbgEng.IDebugClient))(idebug_client)
        hr = debug_create_func(DbgEng.IDebugClient._iid_, idebug_client_ptr)
        if (hr != S_OK):
            raise DebuggerException("DebugCreate() failed with %x" % hr)
        return idebug_client

    if DBGENG_DLL is None:
        load_dbgeng_dlls()

    return debug_create(DBGENG_DLL)
