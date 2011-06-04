#!C:\python27\python.exe

import sys
import buggery
from buggery import idebug

class Tracer(object):
    def __init__(self):
        self.dbg = buggery.Debugger()
        self.dbg.set_event_handler("CREATEPROCESS", self.onCreateProcess)
        self.dbg.add_interest(idebug.DbgEng.DEBUG_EVENT_CREATE_PROCESS)

    def onCreateProcess(self, event):
        print "Create Process:", repr(event)
        print "Registering onLoadModule callback"

        self.dbg.set_event_handler("LOADMODULE", self.onLoadModule)
        self.dbg.add_interest(idebug.DbgEng.DEBUG_EVENT_LOAD_MODULE)

    def onLoadModule(self, event):
        print "LoadModule:", repr(event)

    def run(self):
        self.dbg.spawn("notepad.exe")
        while True:
            self.dbg.wait_for_event()

def main(args):
    tracer = Tracer()
    tracer.run()

if __name__ == "__main__":
    main(sys.argv)
