

class BaseOpenTSDBBackend(object):

    def __init__(self):
        raise NotImplementedError("Subclasses must implement __init__")

    def handle(self, line):
        """handle

        handle a line from tcp

        @param line - line read from tcp socket

        @returns - what to return to the tcp client
        """
        raise NotImplementedError("Subclasses must implement __init__")


class MockOpenTSDBBackend(BaseOpenTSDBBackend):

    def __init__(self):
        print "MockOpenTSDBBackend init"

    def handle(self, line):

        if line == "version\n":
            return "Fake OpenTSDB"


class ForwardingOpenTSDBBackend(BaseOpenTSDBBackend):

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def handle(self, line):

        # TODO: open socket, return
        return None
