import socket
import logging

from opentsdbproxy.exceptions import ConfigurationException

log = logging.getLogger(__name__)


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
        log.debug("MockOpenTSDBBackend init")
        self.messages = []

    def handle(self, message):

        self.messages.append(message)
        log.debug("MockOpenTSDBBackend got message: '%s'" % message)

        if message == "version\n":
            return "Fake OpenTSDB"
        else:
            return None


class ForwardingOpenTSDBBackend(BaseOpenTSDBBackend):

    connection = None

    def __init__(self, host=None, port=None):
        if host is None or port is None:
            raise ConfigurationException("%s requires a host and port to be configured" % self.__class__.__name__)

        self.host = host
        self.port = port
        self.alive = True
        self.tsd = None
        self.last_verify = 0
        self.buffer_size = 4096

    def connect(self):
        """connect to OpenTSDB. Taken from tcollector
        """

        adresses = socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC,
                                      socket.SOCK_STREAM, 0)
        for family, socktype, proto, canonname, sockaddr in adresses:
            try:
                connection = socket.socket(family, socktype, proto)
                connection.settimeout(1)
                connection.connect(sockaddr)
                return connection
            except socket.error, msg:
                log.warning('Connection attempt failed to %s:%d: %s',
                            self.host, self.port, msg)
            return None

    def handle(self, message):

        if self.connection is None:
            self.connection = self.connect()
            if self.connection is None:
                raise Exception("Couldn't connect to OpenTSDB %s:%s" % (self.host, self.port))
        self.connection.sendall(message)
        try:
            response = ''
            while True:
                recv = self.connection.recv(self.buffer_size)
                response += recv
                if len(recv) < self.buffer_size:
                    break
            return recv
        except socket.error:
            log.debug("Socket error to %s:%s" % (self.host, self.port))
            return None


class DjangoAuthorizingBackend(ForwardingOpenTSDBBackend):
    pass


backends = {
    'mock': MockOpenTSDBBackend,
    'forwarding': ForwardingOpenTSDBBackend,
    'django_authz': DjangoAuthorizingBackend,
}
