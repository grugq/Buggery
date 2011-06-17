#!c:\python27\python.exe

import sys
import buggery
from buggery import idebug

class Tracer(object):
    def __init__(self):
        self.dbg = buggery.Debugger()
        self.dbg.set_event_handler("CREATEPROCESS", self.onCreateProcess)
        self.dbg.add_interest(idebug.DbgEng.DEBUG_EVENT_CREATE_PROCESS)

    def onCreateProcess(self, event):
        self.dbg.add_interest(idebug.DbgEng.DEBUG_EVENT_BREAKPOINT)
        self.insert_bps()

    def insert_bps(self):
        sys.stdout.write("process create, insering breakpoints...\n")
        bp = self.dbg.breakpoint(0x01002936, self.onBreakpoint)
        bp = self.dbg.watchpoint(0x01002936, size=1, mode='x', callback=self.onBreakpoint)

    def onBreakpoint(self, bp):
        print "breakpoint:", bp.id

    def run(self):
        self.dbg.spawn("notepad.exe")
        while True:
            try:
                self.dbg.wait_for_event(100)
            except:
                print "Got an exception, I don't want to play anymore."
                break

def main(args):
    tracer = Tracer()
    tracer.run()

if __name__ == "__main__":
    main(sys.argv)
