
class FunctionSandwich(object):
    def __init__(self, dbg, func_name, on_enter, on_exit, *args, **kwargs):
        self.dbg = dbg
        self.func_name = func_name
        self.on_enter = on_enter
        self.on_exit = on_exit
        self.args = args
        self.kwargs = kwargs
        self._bp_id = None

    def inject(self):
        bp = self.dbg.breakpoint(self.func_name,callback=self._on_enter)
        self._bp_id = bp.id
        bp.enable()

    def remove(self):
        if self._bp_id is not None:
            self.dbg.control.remove_breakpoint(self._bp_id)
            self._bp_id = None

    def _on_enter(self, bp, *args, **kwargs):
        # run the pre-function callback, keep retval for on_exit_cb()
        args = self.on_enter(*self.args, **self.kwargs)

        # set the exit hook
        threadid = self.dbg.systemobjects.get_event_thread()
        retaddr = self.dbg.control.get_return_address()


        nbp = self.dbg.add_breakpoint(retaddr, oneshot=True,
                                      callback=self._on_exit,
                                      args=args)
        # multi thread safe, fuck yeah!
        nbp.set_match_thread_id(threadid)

    def _on_exit(self, bp, retargs, *args, **kwargs):
        regs = { 4: "eax", 8: "rax" }
        retreg = regs[self.dbg.ptr_size]

        retval = self.dbg.registers[retreg]

        self.on_exit(retval, retargs)
