
import idebug
import sys
from contextlib import contextmanager


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

    @contextmanager
    def collect(self):
        self.start()
        try:
            yield self
        finally:
            self.stop()

    def __str__(self):
         return "\n".join(self.get_output())

class DebugEventHandler(idebug.EventHandler):
    INTEREST_MASK = (idebug.DbgEng.DEBUG_EVENT_BREAKPOINT |
                     idebug.DbgEng.DEBUG_EVENT_CREATE_PROCESS |
                     idebug.DbgEng.DEBUG_EVENT_EXCEPTION)

    def __init__(self, interestmask):
        if interestmask is not None:
            self.INTEREST_MASK = interestmask
        self.handlers = {
            'INTERESTMASK': self.get_interest_mask,
            'BREAKPOINT': self._on_breakpoint
            'EXCEPTION': idebug.DbgEng.DEBUG_EVENT_EXCEPTION
        }
        self._bp_callbacks = {}

    def get_interest_mask(self, ignored):
        return self.INTEREST_MASK
    def set_interest_mask(self, interest_mask):
        self.INTEREST_MASK = interest_mask
    def add_interest(self, interest):
        self.INTEREST_MASK |= interest
    def has_interest(self, interest):
        return bool(self.INTEREST_MASK & interest)

    def _on_breakpoint(self, bp):
        if bp.id in self._bp_callbacks:
            handler,args,kwargs = self._bp_callbacks[bp.id]
            return handler(bp, *args, **kwargs)

    def handle_event(self, eventtype, event):
        try:
            retval = None
            retval = self.handlers[eventtype](event)
        except KeyError:
            retval = idebug.GO_HANDLED
        except Exception, e:
            sys.stderr.write("%r" % e)
            retval = idebug.GO_IGNORED

        if retval is None:
            retval = idebug.GO_HANDLED

        return retval

    def set_handler(self, eventtype, handler):
        self.handlers[eventtype] = handler

class AddressSpace(object):
    def __init__(self, dbg):
        self.dbg = dbg
    def __getitem__(self, offset):
        if isinstance(offset, (slice,)):
            address, count = offset.start, offset.stop-offset.start
        else:
            address, count = offset, 1
        return self.dbg.dataspaces.read(address, count)
    def __setitem__(self, offset, buf):
        if isinstance(offset, (slice,)):
            address, count = offset.start, offset.stop-offset.start
            if len(buf) != count:
                raise RuntimeError("Buffer size and slice range don't agree: %d != %d" % (len(buf), count))
        else:
            address, count = offset, len(buf)
        num = self.dbg.dataspaces.write(offset, buf)

        if num != count:
            raise RuntimeError("Short write to memory %d < %d. Inconsistent state, bailing out...", num, count)
        return self

    def find(self, pattern, address, count, alignment=1):
        return self.dbg.dataspaces.search(pattern, address, count, alignment)
        
    def unpack(self, fmt, addr):
        st = struct.Struct(fmt)
        buf = self.dbg.dataspaces.read(addr, st.size)
        return st.unpack(buf)
    def pack(self, fmt, addr, *args):
        st = struct.Struct(fmt)
        buf = st.pack(fmt, *args)
        return self.dbg.dataspaces.write(addr, buf)
    # stupid convenience functions
    def get_int8(self, addr): return self.unpack('c', addr)
    def put_int8(self, addr, val): return self.pack('c', addr, val)
    def get_uint8(self, addr): return self.unpack('C', addr)
    def put_uint8(self, addr, val): return self.pack('C', addr, val)
    def get_int16(self, addr): return self.unpack('h', addr)
    def put_int16(self, addr, val): return self.pack('h', addr, val)
    def get_uint16(self, addr): return self.unpack('H', addr)
    def put_uint16(self, addr, val): return self.pack('H', addr, val)
    def get_int32(self, addr): return self.unpack('i', addr)
    def put_int32(self, addr, val): return self.pack('i', addr, val)
    def get_uint32(self, addr): return self.unpack('I', addr)
    def put_uint32(self, addr, val): return self.pack('I', addr, val)
    def get_int64(self, addr): return self.unpack('q', addr)
    def put_int64(self, addr, val): return self.pack('q', addr, val)
    def get_uint64(self, addr): return self.unpack('Q', addr)
    def put_uint64(self, addr, val): return self.pack('Q', addr, val)
    def get_pointer(self, addr):
        if self.dbg.control.is_pointer_64bit():
            return self.get_uint64(addr)
        return self.get_uint32(addr)
    def put_pointer(self, addr, value):
        # ??? how to get 64bit ???
        if self.dbg.control.is_pointer_64bit():
            return self.put_uint64(addr, value)
        return self.put_uint32(addr, value)


class Debugger(object):
    def __init__(self, interestmask=None):
        self._output = CollectOutputCallbacks()
        self._events = DebugEventHandler(interestmask)
        self.client = idebug.Client(output_cb=self._output,
                                   event_cb=self._events)

        self.dataspaces = idebug.DataSpaces(self.client)
        self.registers = idebug.Registers(self.client)
        self.control = idebug.Control(self.client)
        #
        self.addrspace = AddressSpace(self)

    def set_event_handler(self, eventtype, handler):
        interests = {
            'BREAKPOINT': idebug.DbgEng.DEBUG_EVENT_BREAKPOINT,
            'CREATEPROCESS': idebug.DbgEng.DEBUG_EVENT_CREATE_PROCESS,
            'EXCEPTION': idebug.DbgEng.DEBUG_EVENT_EXCEPTION
        }
        self._events.set_handler(eventtype, handler)
        # should adjust set_interest_mask too
        if eventtype in interests \
                and not self._events.has_interest(interests[eventtype]):
            self.add_interest(interests[eventtype])

    def add_interest(self, interest):
        self._events.add_interest(interest)
        self.client.set_event_callbacks(self._events)

    def set_interest_mask(self, interest_mask):
        # Assuming that we can just add new interests like this
        self._events.set_interest_mask(interest_mask)
        return self.client.set_event_callbacks(self._events)

    def execute(self, cmd):
        with self._output.collect():
            self.control.execute(cmd)
            self.client.flush_output()
            return str(self._output)

    def step_into(self): pass
    def step_over(self): pass
    def step_branch(self): pass

    def breakpoint(self, address, callback,oneshot=False,private=True,cmd=None,
                  args=None, kwargs=None):
        bp = self.control.set_breakpoint(address, oneshot, private, cmd)
        self._events._bp_callbacks[bp.id] = callback,args,kwargs
        return bp

    def watchpoint(self, address, size, callback, mode='rwx', oneshot=False,private=True,cmd=None):
        bp = self.control.set_watchpoint(address, size, mode, oneshot, private, cmd)
        self._events._bp_callbacks[bp.id] = callback
        return bp

    @property
    def ptr_size(self):
        return 8 if self.control.is_pointer_64bit() else 8

    def read_args(self, argstr, use_frame=False):
        '''read_args( argstr ) -> tuple(arg0, arg1, ..., argN)

        argstr := struct.unpack() string of argument types
        '''
        # common case: bpx at the start of a function, before the prologue
        if use_frame:
            stack = self.registers.getframe()
        else:
            stack = self.registers.getstack()
        # need to adjust stack ptr up by sizeof(return address)
        ret_addr_size = self.ptr_size
        return self.dataspaces.unpack(argstr, stack + ret_addr_size)

    def wait_for_event(self):
        return self.control.wait_for_event()

    def next_event(self):
        self.wait_for_event()
        return self.control.get_last_event()

    def spawn(self, cmdline):
        self.client.create_process(cmdline)

    def attach(self, pid, flags=None):
        self.client.attach_process(pid, flags)

    def detach(self):
        self.client.detach_processes()

    def terminate(self):
        self.client.terminate_processes()

    def opendump(self, path):
        self.client.open_dump_file(path)

    def writedump(self, path, mode=0):
        self.client.write_dump_file(path, mode)
