
class CollectOutputCallbacks(OutputCallbacks):
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

class Debugger(idebug.IDebugClient):
    def __init__(self):
        self._output = CollectOutputCallbacks()
        super(Debugger, self).__init__(output_cb=self._output)

    def execute(self, cmd):
        self._output.start()
        super(Debugger, self).execute(cmd)
        self._output.stop()
        return self._output.get_output()
