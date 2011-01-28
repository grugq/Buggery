
import utils
import comtypes
import ctypes as ct
from comtypes import CoClass, GUID
from comtypes.hresult import S_OK, S_FALSE
from comtypes.gen import DbgEng
from collections import namedtuple

class BadRegisterError(RuntimeError): pass


class OutputCallbacks(object):
    def onOutput(self, mask, text): pass


class DebugOutputCallback(CoClass):
    _reg_clsid_ = GUID('{EAC5ACAA-7BD0-4f1f-8DEB-DF2862A7E85B}')
    _reg_threading_ = "Both"
    _reg_progid_ = "DbgEngLib.DbgEngOutputCallbacks.1"
    _reg_novers_progid_ = "DbgEngLib.DbgEngOutputCallbacks"
    _reg_desc_ = "Callback class!"
    _reg_clsctx_ = comtypes.CLSCTX_INPROC_SERVER

    _com_interfaces_ = [DbgEng.IDebugOutputCallbacks,
                        comtypes.typeinfo.IProvideClassInfo2,
                        comtypes.errorinfo.ISupportErrorInfo,
                        comtypes.connectionpoints.IConnectionPointContainer]

    def __init__(self, proxy):
        super(DebugOutputCallback, self).__init__()
        self._proxy = proxy

    def IDebugOutputCallbacks_Output(self, mask, text):
        self._proxy.onOutput(mask, text)
        return S_OK

ExceptionEvent = namedtuple("ExceptionEvent",
                 "code,flags,record,address,information,firstchance")
Breakpoint = namedtuple("Breakpoint", "offset,id,breaktype,proctype,flags,datasize,dataaccesstype,passcount,currentpasscount,matchthread,commandsize,offsetexpressionsize")

class EventCallbacks(object):
    def onGetInterestMask(self): pass
    def onBreakpoint(self, bp): pass
    def onChangeDebuggeeState(self, flags, arg): pass
    def onChangeEngineState(self, flags, arg): pass
    def onException(self, exception): pass
    def onLoadModule(self, imageFileHandle, baseOffset, moduleSize, moduleName,
                     imageName, checkSum, timeDateStamp): pass
    def onUnloadModule(self, imageBaseName, baseOffset): pass
    def onCreateProcess(self, imageFileHandle, handle, baseOffset, moduleSize,
                       moduleName, imageName, checkSum, timeDateStamp,
                       initialThreadHandle, threadDataOffset, startOffset): pass
    def onExitProcess(self, exitCode): pass
    def onSessionStatus(self, status): pass
    def onChangeSymbolState(self, flags, arg): pass
    def onSystemError(self, error, level): pass
    def onCreateThread(self,handle, dataOffset, startOffset): pass
    def onExitThread(self, exitCode): pass


class DebugEventCallbacks(CoClass):
    _reg_clsid_ = GUID('{EAC5ACAA-7BD0-4f1f-8DEB-DF2862A7E85B}')
    _reg_threading_ = "Both"
    _reg_progid_ = "DbgEngLib.DbgEngEventCallbacks.1"
    _reg_novers_progid_ = "DbgEngLib.DbgEngEventCallbacks"
    _reg_desc_ = "Callback class!"
    _reg_clsctx_ = comtypes.CLSCTX_INPROC_SERVER

    _com_interfaces_ = [DbgEng.IDebugEventCallbacks,
                        comtypes.typeinfo.IProvideClassInfo2,
                        comtypes.errorinfo.ISupportErrorInfo,
                        comtypes.connectionpoints.IConnectionPointContainer]

    def __init__(self, proxy):
        super(DebugEventCallbacks, self).__init__()
        self._proxy = proxy

    def IDebugEventCallbacks_GetInterestMask(self, mask=None):
        return self._proxy.onGetInterestMask()

    def IDebugEventCallbacks_Breakpoint(self, bp):
        p = bp.getParams()
        bp = Breakpoint(p.Offset, p.Id, p.BreakType, p.ProcType, p.Flags,
                        p.DataSize, p.DataAccessType, p.PassCount,
                        p.CurrentPassCount, p.MatchThread, p.CommandSize,
                        p.OffsetExpressionSize)
        return self._proxy.onBreakpoint(bp)

    def IDebugEventCallbacks_ChangeDebuggeeState(self, flags, arg):
        return self._proxy.onChangeDebuggeeState(flags, arg)

    def IDebugEventCallbacks_ChangeEngineState(self, flags, arg):
        return self._proxy.onChangeEngineState(flags, arg)

    def IDebugEventCallbacks_Exception(self, exception, firstChance):
        ex = exception.contents
        info = [ex.ExceptionInformation[i] for i in xrange(ex.NumberParameters)]
        event = ExceptionEvent(ex.ExceptionCode, ex.ExceptionFlags,
                               ex.ExceptionRecord, ex.ExceptionAddress,
                               info, firstChance)
        return self._proxy.onException(event)

    def IDebugEventCallbacks_LoadModule(self, imageFileHandle, baseOffset,
                                        moduleSize, moduleName, imageName,
                                        checkSum, timeDateStamp):
        return self._proxy.onLoadModule(imageFileHandle, baseOffset, moduleSize,
                                      moduleName, imageName, checkSum,
                                      timeDateStamp)

    def IDebugEventCallbacks_UnloadModule(self, imageBaseName, baseOffset):
        return self._proxy.onUnloadModule(imageBaseName, baseOffset)

    def IDebugEventCallbacks_CreateProcess(self, imageFileHandle, handle,
                                           baseOffset, moduleSize,
                                           moduleName, imageName, checkSum,
                                           timeDateStamp,
                                           initialThreadHandle,
                                           threadDataOffset, startOffset):
        return self._proxy.onCreateProcess(imageFileHandle, handle, baseOffset,
                                         moduleSize, moduleName, imageName,
                                         checkSum, timeDateStamp,
                                         initialThreadHandle, threadDataOffset,
                                         startOffset)

    def IDebugEventCallbacks_ExitProcess(self, exitCode):
        return self._proxy.onExitProcess(exitCode)

    def IDebugEventCallbacks_SessionStatus(self, status):
        return self._proxy.onSessionStatus(unknown, status)

    def IDebugEventCallbacks_ChangeSymbolState(self, flags, arg):
        return self._proxy.onChangeSymbolState(flags, arg)

    def IDebugEventCallbacks_SystemError(self, error, level):
        return self._proxy.onSystemError(error, level)

    def IDebugEventCallbacks_CreateThread(self,handle, dataOffset, startOffset):
        return self._proxy.onCreateThread(handle, dataOffset, startOffset)

    def IDebugEventCallbacks_ExitThread(self, exitCode):
        return self._proxy.onExitThread(exitCode)


class Registers(object):
    def __init__(self, client):
        self._client = client
        query_i = self._client.get_com_interface
        self._registers = query_i(interface=DbgEng.IDebugRegisters)
        self._map = None

    def _build_map(self):
        self._map = {}
        for i in xrange(self._registers.GetNumberRegisters()):
            name = self._get_description(i)
            self._map[name] = i

    def _get_description(self, index):
        return self._registers.GetDescription(index, ' '*12, 12)

    def get_value_by_name(self, name):
        if self._map is None:
            self._build_map()

        try:
            index = self._map[name]
        except KeyError:
            raise BadRegisterError("No such registers: %s" % name)

        value = self._registers.GetValue(index)

        for v in ("I64", "I32", "I16", "I8"):
            if hasattr(value.u, v):
                return int(getattr(value.u, v))

    def set_value_by_name(self, name, value):
        if self._map is None:
            self._build_map()
        rval = self._registers.GetValue(self._map[name])
        rval.u.I64 = value # let the union() sort it out..
        self._registers.SetValue(self._map[name], ct.byref(rval))

    def keys(self):
        if self._map is None:
            self._build_map()
        return self._map.keys()

    def values(self):
        if self._map is None:
            self._build_map()

        return [self.get_value_by_name(v) for v in self._map.keys()]

    def iteritems(self):
        if self._map is None:
            self._build_map()
        return [(v,self.get_value_by_name(v)) for v in self._map.keys()]

    def __getitem__(self, name):
        return self.get_value_by_name(name)

    def __setitem__(self, name, value):
        self.set_value_by_name(name, value)

    def __len__(self):
        if self._map is None:
            self._build_map()
        return len(self._map)

    def __getattr__(self, name):
        if self._map is None:
            self._build_map()

        if name not in self._map:
            raise AttributeError("No such register: %s" % name)

        return self.get_value_by_name(name)


class Control(object):
    def __init__(self, client):
        self._client = client
        query_i = self._client.get_com_interface
        self._control  = query_i(interface=DbgEng.IDebugControl)
        self._control2 = query_i(interface=DbgEng.IDebugControl2)
        self._control3 = query_i(interface=DbgEng.IDebugControl3)
        self._control4 = query_i(interface=DbgEng.IDebugControl4)

    def wait_for_event(self, timeout_ms=-1):
        retval = self._control.WaitForEvent(0, timeout_ms)
        if retval != S_OK:
            raise RuntimeError("Something fucked up: %d" % retval)

    def execute(self, cmd):
        self._control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, cmd, 0)

    def assemble(self, address, asm):
        naddress = self._control.Assemble(address, asm)
        return naddress

    def get_execution_status(self):
        status = self._control.GetExecutionStatus()
        return status

    def set_execution_status(self, value):
        self._control.SetExecutionStatus(value)

    def get_last_event(self):
        f = self._control._IDebugControl__com_GetLastEventInformation
        typ = ct.c_ulong()
        pid = ct.c_ulong()
        tid = ct.c_ulong()
        extra = ct.create_string_buffer(1024)
        extra_used = ct.c_ulong()
        desc_used = ct.c_ulong()

        hresult = f(ct.byref(typ), ct.byref(pid), ct.byref(tid),
                    ct.byref(extra), ct.sizeof(extra), ct.byref(extra_used),
                    ' '*256, 256, ct.byref(desc_used))

        if hresult != S_OK:
            raise RuntimeError("Ffuuuuuuuuuck: %d" % hresult)
        return (typ.value, pid.value, tid.value, extra.raw[:extra_used.value])


class DataSpaces(object):
    def __init__(self, client):
        self._client = client
        query_i = self._client.get_com_interface
        self._data_space  = query_i(interface=DbgEng.IDebugDataSpaces)
        self._data_space2 = query_i(interface=DbgEng.IDebugDataSpaces2)
        self._data_space3 = query_i(interface=DbgEng.IDebugDataSpaces3)
        self._data_space4 = query_i(interface=DbgEng.IDebugDataSpaces4)

    def read(self, address, count):
        buf = ct.create_string_buffer(count)
        nbytes = ct.c_ulong()

        f = self._data_space._IDebugDataSpace__com_ReadVirtualUncached
        hresult = f(ct.c_ulonglong(address), ct.byref(buf), ct.sizeof(buf),
                    ct.byref(nbytes))
        if hresult != S_OK:
            raise RuntimeError("Fuck, that didn't work: %d" % hresult)
        return buf.raw[:nbytes.value]

    def write(self, address, buf):
        raise NotImplementedError("sorry, not done yet")

    def search(self, pattern, address=None, length=None):
        raise NotImplementedError("sorry, not done yet")


class Symbols(object):
    def __init__(self, client):
        self._client = client
        query_i = self._client.get_com_interface
        self._symbols = query_i(interface=DbgEng.IDebugSymbols)

class SystemObjects(object):
    def __init__(self, client):
        self._client = client
        query_i = self._client.get_com_interface
        self._system_objects  = query_i(interface=DbgEng.IDebugSystemObjects)
        self._system_objects2 = query_i(interface=DbgEng.IDebugSystemObjects2)
        self._system_objects3 = query_i(interface=DbgEng.IDebugSystemObjects3)


class Client(object):
    def __init__(self, event_cb=None, output_cb=None, input_cb=None):
        self._client = utils.create_idebug_client()

        if event_cb is not None:
            self.set_event_callbacks(event_cb)
        if output_cb is not None:
            self.set_output_callbacks(output_cb)
        if input_cb is not None:
            self.set_input_callbacks(input_cb)

    def get_com_interface(self, interface):
        return self._client.QueryInterface(interface=interface)

    def set_event_callbacks(self, event_callbacks):
        event_proxy = DebugEventCallbacks(event_callbacks)
        event_proxy.IUnknown_AddRef(event_proxy)

        self._client.SetEventCallbacks(Callbacks=event_proxy)

    def set_output_callbacks(self, output_callbacks):
        output_proxy = DebugOutputCallback(output_callbacks)
        output_proxy.IUnknown_AddRef(output_proxy)

        self._client.SetOutputCallbacks(Callbacks=output_proxy)

    def set_input_callbacks(self, input_callbacks): pass

    def write(self, buf):
        retval = self._client.ReturnInput(buf)
        if retval != S_OK:
            return None
        return len(buf)

    def flush_output(self):
        self._client.FlushCallbacks()

    def create_process(self, cmd_line, follow_forks=False):
        if follow_forks:
            flags = DbgEng.DEBUG_PROCESS
        else:
            flags = DbgEng.DEBUG_ONLY_THIS_PROCESS

        self._client.CreateProcess(0, CommandLine=cmd_line, CreateFlags=flags)

    def attach_process(self, pid):
        flags = DbgEng.DEBUG_ATTACH_DEFAULT
        self._client.AttachProcess(0, ProcessId=pid, AttachFlags=flags)

    def open_dumpfile(self, path):
        self._client.OpenDumpFile(path)

    def write_dumpfile(self, path, mode=0):
        '''write_dumpfile(path, mode)

        mode -> 0 == DEBUG_DUMP_DEFAULT
        mode -> 1 == DEBUG_DUMP_SMALL
        mode -> 2 == DEBUG_DUMP_FULL
        '''
        if mode == 0:
            mode = DbgEng.DEBUG_DUMP_DEFAULT
        elif mode == 1:
            mode = DbgEng.DEBUG_DUMP_SMALL
        elif mode == 2:
            mode = DbgEng.DEBUG_DUMP_FULL
        self._client.WriteDumpFile(path, mode)

    def terminate_processes(self):
        self._client.TerminateProcesses()

    def detach_processes(self):
        self._client.DetachProcesses()

    def get_exit_code(self):
        return self._client.GetExitCode()
