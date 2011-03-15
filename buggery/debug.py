
import idebug

# thinking about doing this via contextmanager
# with output(dbg.execute(cmd))

class CollectOutputCallbacks(idebug.OutputCallbacks):
    def __init__(self):
        self._collection = []
        self._gathering = False

    def onOutput(self, mask, text):
        if self._gathering:
            self._collection.append(text)

    def start(self):
        self._collection = []
        self._gathering = True
    def stop(self):
        self._gathering = False
    def get_output(self):
        return self._collection

class CollectEventCallbacks(idebug.EventCallbacks):
    INTEREST_MASK = (idebug.DbgEng.DEBUG_EVENT_BREAKPOINT |
                     idebug.DbgEng.DEBUG_EVENT_EXCEPTION)

    def get_interest_mask(self):
        return self.INTEREST_MASK

    def handle_event(self, eventtype, event):
        pass

    def onGetInterestMask(self):
        return self.get_interest_mask()

    def onBreakpoint(self, bp):
        return self.handle_event('BREAKPOINT', bp)

    def onChangeDebuggeeState(self, flags, arg):
        return self.handle_event('DEBUGEESTATE', (flags, arg))

    def onChangeEngineState(self, flags, arg):
        return self.handle_event('ENGINESTATE', (flags, arg))

    def onException(self, exception):
        return self.handle_event('EXCEPTION', exception)

    def onLoadModule(self, imageFileHandle, baseOffset, moduleSize, moduleName,
                     imageName, checkSum, timeDateStamp):
        return self.handle_event('LOAD', ())

    def onUnloadModule(self, imageBaseName, baseOffset):
        return self.handle_event('UNLOAD', (imageBaseName, baseOffset))

    def onCreateProcess(self, imageFileHandle, handle, baseOffset, moduleSize,
                       moduleName, imageName, checkSum, timeDateStamp,
                       initialThreadHandle, threadDataOffset, startOffset): pass

    def onExitProcess(self, exitCode): pass
    def onSessionStatus(self, status): pass
    def onChangeSymbolState(self, flags, arg): pass
    def onSystemError(self, error, level): pass
    def onCreateThread(self,handle, dataOffset, startOffset): pass
    def onExitThread(self, exitCode): pass

class Debugger(object):
    def __init__(self):
        self._output = CollectOutputCallbacks()
        self.client = idebug.Client(output_cb=self._output)
        self.dataspaces = idebug.DataSpaces(self.client)
        self.registers = idebug.Registers(self.client)
        self.control = idebug.Control(self.client)

    def execute(self, cmd):
        self._output.start()
        self.control.execute(cmd)
        self.client.flush_output()
        self._output.stop()
        return self._output.get_output()

    def step_into(self):
        pass
    def step_over(self):
        pass
    def step_branch(self):
        pass

    def wait_for_event(self):
        return self.control.wait_for_event()

    def next_event(self):
        self.wait_for_event()
        return self.control.get_last_event()

    def spawn(self, cmdline):
        self.client.create_process(cmdline)

    def attach(self, pid):
        self.client.attach_process(pid)

    def detach(self):
        self.client.detach_processes()

    def terminate(self):
        self.client.terminate_processes()

    def opendump(self, path):
        self.client.open_dump_file(path)

    def writedump(self, path, mode=0):
        self.client.write_dump_file(path, mode)
