#!c:\python27\python.exe

import sys
import buggery
from buggery import idebug

class Tracer(object):
    def __init__(self):
        self.dbg = buggery.Debugger()
        self.dbg.set_event_handler("EXCEPTION", self.onException)


    def onException(self, exception):
        print "EXCEPTION:"
        print exception

    def run(self):
        self.dbg.spawn("exception.exe")
        while True:
            try:
                self.dbg.wait_for_event()
            except Exception, msg:
                print "Got an exception, I don't want to play anymore."
                print msg
                break

def main(args):
    tracer = Tracer()
    tracer.run()

if __name__ == "__main__":
    main(sys.argv)
