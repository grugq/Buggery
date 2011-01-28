
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
