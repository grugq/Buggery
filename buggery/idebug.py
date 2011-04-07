
import comtypes
import ctypes as ct
from comtypes import CoClass, GUID
from comtypes.hresult import S_OK, S_FALSE
from comtypes.gen import DbgEng
from collections import namedtuple
import struct

import utils

class BadRegisterError(RuntimeError): pass


GO_HANDLED = DbgEng.DEBUG_STATUS_GO_HANDLED
GO_NOT_HANDLED = DbgEng.DEBUG_STATUS_GO_NOT_HANDLED
GO_IGNORED = DbgEng.DEBUG_STATUS_IGNORE_EVENT


class Breakpoint(object):
    def __init__(self, bp):
        self.bp = bp
    @property
    def id(self):
        return self.bp.GetId()

    def enable(self):
        self.bp.AddFlags(DbgEng.DEBUG_BREAKPOINT_ENABLED)
    def disable(self):
        self.bp.RemoveFlags(DbgEng.DEBUG_BREAKPOINT_ENABLED)
    def isenabled(self):
        return self.bp.GetFlags() & DbgEng.DEBUG_BREAKPOINT_ENABLED

    @property
    def command(self):
        return self.bp.GetCommand()
    @command.setter
    def set_command(self, cmd):
        self.bp.SetCommand(cmd)

    @property
    def passcount(self):
        return self.bp.GetPassCount()
    @passcount.setter
    def set_passcount(self, count):
        self.bp.SetPassCount(count)

    @property
    def offset(self):
        return self.bp.GetOffset()
    @offset.setter
    def set_offset(self, offset):
        self.bp.SetOffset(offset)

    @property
    def offsetexpression(self):
        return self.bp.GetOffsetExpression()
    @offsetexpression.setter
    def set_offsetexpression(self, offexpr):
        self.bp.SetOffsetExpression(offexpr)

class Watchpoint(Breakpoint):
    @property
    def size(self):
        size, accesstype = self.bp.GetDataParameters()
        return size
    @size.setter
    def set_size(self, size):
        old, accesstype = self.bp.GetDataParameters()
        self.bp.SetDataParameters(size, accesstype)

    @property
    def accesstype(self):
        size, access = self.GetDataParameters()
        rv = ""
        rv += 'r' if access & DbgEng.DEBUG_BREAK_READ else '-'
        rv += 'w' if access & DbgEng.DEBUG_BREAK_WRITE else '-'
        rv += 'x' if access & DbgEng.DEBUG_BREAK_EXECUTE else '-'
        return rv
    @accesstype.setter
    def set_accesstype(self, access):
        size, old = self.GetDataParameters()
        accesstype = 0
        if 'r' in access:
            accesstype |= DbgEng.DEBUG_BREAK_READ
        if 'w' in access:
            accesstype |= DbgEng.DEBUG_BREAK_WRITE
        if 'x' in access:
            accesstype |= DbgEng.DEBUG_BREAK_EXECUTE
        self.bp.SetDataParameters(size, accesstype)


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
ExceptionInformation = namedtuple("ExceptionInformation",
            "code, flags, record, address, nparams, av_flag, av_address, info")

ChangeSymbolStateEvent = namedtuple("ChangeSymbolStateEvent", "flags, arg")
ChangeDebuggeeStateEvent = namedtuple("ChangeDebuggeeStateEvent", "flags, arg")
ChangeEngineStateEvent = namedtuple("ChangeEngineStateEvent", "flags, arg")
ChangeSymbolStateEvent = namedtuple("ChangeSymbolStateEvent", "flags, arg")
LoadModuleEvent = namedtuple("LoadModuleEvent",
    "imageFileHandle, baseOffset, moduleSize, moduleName, imageName, checkSum, timeDateStamp")
UnloadModuleEvent = namedtuple("UnloadModuleEvent", "imageBaseName, baseOffset")
CreateProcessEvent = namedtuple("CreateProcessEvent",
"imageFileHandle, handle, baseOffset, moduleSize, moduleName, imageName, checkSum, timeDateStamp, initialThreadHandle, threadDataOffset, startOffset")
SystemErrorEvent = namedtuple("SystemErrorEvent", "error, level")
CreateThreadEvent = namedtuple("CreateThreadEvent", "handle, dataOffset, startOffset")


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


class EventHandler(EventCallbacks):
    def handle_event(self, evtype, event):
        pass

    def onGetInterestMask(self):
        return self.handle_event('INTERESTMASK', None)

    def onBreakpoint(self, bp):
        if bp.GetType() == DbgEng.DEBUG_BREAKPOINT_CODE:
            bp = Breakpoint(bp)
        else:
            bp = Watchpoint(bp)
        return self.handle_event('BREAKPOINT', bp)

    def onChangeDebuggeeState(self, flags, arg):
        event = ChangeDebuggeeStateEvent(flags, arg)
        return self.handle_event('DEBUGEESTATE', event)

    def onChangeEngineState(self, flags, arg):
        event = ChangeEngineStateEvent(flags, arg)
        return self.handle_event('ENGINESTATE', (flags, arg))

    def onException(self, exception):
        return self.handle_event('EXCEPTION', exception)

    def onLoadModule(self, imageFileHandle, baseOffset, moduleSize, moduleName,
                     imageName, checkSum, timeDateStamp):
        event = LoadModuleEvent(imageFileHandle, baseOffset, moduleSize,
                                moduleName, imageName, checkSum, timeDateStamp)
        return self.handle_event('LOADMODULE', event)

    def onUnloadModule(self, imageBaseName, baseOffset):
        event = UnloadModuleEvent(imageBaseName, baseOffset)
        return self.handle_event('UNLOADMODULE', event)

    def onCreateProcess(self, imageFileHandle, handle, baseOffset, moduleSize,
                       moduleName, imageName, checkSum, timeDateStamp,
                       initialThreadHandle, threadDataOffset, startOffset):
        event = CreateProcessEvent(imageFileHandle, handle, baseOffset,
                                   moduleSize, moduleName, imageName, checkSum,
                                   timeDateStamp, initialThreadHandle,
                                   threadDataOffset, startOffset)
        return self.handle_event('CREATEPROCESS', event)

    def onExitProcess(self, exitCode):
        return self.handle_event('EXITPROCESS', exitCode)

    def onSessionStatus(self, status):
        return self.handle_event('SESSIONSTATUS', status)

    def onChangeSymbolState(self, flags, arg):
        event = ChangeSymbolStateEvent(flags, arg)
        return self.handle_event('SYMBOLSTATE', event)

    def onSystemError(self, error, level):
        event = SystemErrorEvent(error, level)
        return self.handle_event('SYSTEMERROR', event)

    def onCreateThread(self,handle, dataOffset, startOffset):
        event = CreateThreadEvent(handle, dataOffset, startOffset)
        return self.handle_event('CREATETHREAD', event)

    def onExitThread(self, exitCode):
        return self.handle_event('EXITTHREAD', exitCode)


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
        return self._proxy.onLoadModule(imageFileHandle, baseOffset,
                                        moduleSize, moduleName, imageName,
                                        checkSum, timeDateStamp)

    def IDebugEventCallbacks_UnloadModule(self, imageBaseName, baseOffset):
        event = UnloadModuleEvent(imageBaseName, baseOffset)
        return self._proxy.onUnloadModule(event)

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
        return self._proxy.onSessionStatus(status)

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

        for v in ("I64", "I32", "I16", "I8"):
            if hasattr(rval.u, v):
                setattr(rval.u, v, value) # let the union {} sort it out...

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

    def __contains__(self, name):
        if self._map is None:
            self._build_map()
        return name in self._map

    def __getattr__(self, name):
        if name not in self:
            raise AttributeError("No such register: %s" % name)
        return self.get_value_by_name(name)

class BreakpointList(object):
    def __init__(self, control):
        self._control = control
    def __len__(self):
        return self._control.GetNumberBreakpoints()
    def __getitem__(self, index):
        if index < len(self):
            bp = self._control.GetBreakpointByIndex(index)
        else:
            bp = self._control.GetBreakpointById(index)
        return BreakpointControl(bp)

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
        desc = ct.create_string_buffer(1024)
        extra_used = ct.c_ulong()
        desc_used = ct.c_ulong()

        hresult = f(ct.byref(typ), ct.byref(pid), ct.byref(tid),
                    ct.byref(extra), ct.sizeof(extra), ct.byref(extra_used),
                    desc, ct.sizeof(desc), ct.byref(desc_used))

        if hresult != S_OK:
            raise RuntimeError("Ffuuuuuuuuuck: %d" % hresult)
        return (typ.value, pid.value, tid.value, extra.raw[:extra_used.value])

    def get_access_violation_event(self):
        avtype, pid, tid, extra = self.get_last_event()
        extra = struct.unpack("IIQQII16Q", extra)

        exinfo = ExceptionInformation(extra[0], extra[1], extra[2], extra[3],
                                      extra[4], extra[6], extra[7], extra[8:])
        return avtype, pid, tid, exinfo

    def _new_breakpoint(self, bptype, oneshot=False, private=False, cmd=None):
        bp = self._control.AddBreakpoint(bptype, DbgEng.DEBUG_ANY_ID)
        if oneshot:
            bp.AddFlags(DbgEng.DEBUG_BREAKPOINT_ONE_SHOT)
        if private:
            bp.AddFlags(DbgEng.DEBUG_BREAKPOINT_ADDER_ONLY)
        if cmd is not None:
            bp.SetCommand(cmd)
        return bp

    def set_watchpoint(self, address, size, mode='rwx', oneshot=False,
                           private=False, cmd=None):
        bp = self._new_breakpoint(DbgEng.DEBUG_BREAKPOINT_DATA,oneshot,private,cmd)

        bpmode = 0
        if 'r' in mode:
            bpmode |= DbgEng.DEBUG_BREAK_READ
        if 'w' in mode:
            bpmode |= DbgEng.DEBUG_BREAK_WRITE
        if 'x' in mode:
            bpmode |= DbgEng.DEBUG_BREAK_EXECUTE

        bp.SetDataParameters(size, bpmode)
        bp.AddFlags(DbgEng.DEBUG_BREAKPOINT_ENABLED)
        return Watchpoint(bp)

    def set_breakpoint(self, address, oneshot=False, private=False, cmd=None):
        def get_address(address):
            if isinstance(address, (str, unicode)):
                try:
                    address = int(address)
                except ValueError:
                    if address.startswith("0x"):
                        address = int(address, 16)
                    else:
                        address = None
            return address

        bp = self._new_breakpoint(DbgEng.DEBUG_BREAKPOINT_CODE,oneshot,private,cmd)

        addr = get_address(address)
        if addr is not None:
            bp.SetOffset(address)
        else:
            bp.SetOffsetExpression(address)

        bp.AddFlags(DbgEng.DEBUG_BREAKPOINT_ENABLED)
        return Breakpoint(bp)

    def get_number_breakpoints(self):
        return self._control.GetNumberBreakpoints()
    def get_breakpoint_by_index(self, ndx):
        bp = self._control.GetBreakpointByIndex(ndx)
        return bp
    def get_breakpoint_by_id(self, bpid):
        bp = self._control.GetBreakpointById(bpid)
        return bpid
    def remove_breakpoint(self, bpid=None, ndx=None):
        if bpid is not None:
            bp = self._control.GetBreakpointById(bpid)
        elif ndx is not None:
            bp = self._control.GetBreakpointByIndex(ndx)
        else:
            raise RuntimeError("Kinda need either an index or an ID, you know?")
        return self._control.RemoveBreakpoint(bp)

    def add_extension(self, path):
        return self._control.AddExtention(path, 0)
    def remove_extension(self, handle):
        self._control.RemoveExtension(handle)
    def get_extension_by_path(self, path):
        handle = self._control.GetExtensionByPath(path)
        return handle.value
    def call_extension(self, handle, extension, args):
        return self._control.CallExtension(handle, extension, args)


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
    DEFAULT_PATH=r'''SRV*%SYSTEMROOT%\localsymbols*http://msdl.microsoft.com/download/symbols'''
    def __init__(self, client):
        self._client = client
        query_i = self._client.get_com_interface
        self._symbols = query_i(interface=DbgEng.IDebugSymbols)
    def set_symbol_path(self, path=None):
        if path is None:
            path = self.DEFAULT_PATH
        return self._symbols.SetSymbolPath(path)

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
