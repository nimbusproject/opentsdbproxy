import logging

from gevent.server import StreamServer
from gevent.pool import Pool

from opentsdbproxy.backends import backends
from opentsdbproxy.exceptions import ConfigurationException

log = logging.getLogger(__name__)

__version__ = "0.1.2"
__fullversion__ = "OpenTSDB Proxy %s" % __version__

MAX_CONNECTIONS = 10000
BUF_SIZE = 4096
DEFAULT_PORT = 4242
DEFAULT_BACKEND_PARAMS = {}


class OpenTSDBProxy(object):

    def __init__(self, port=None, backend=None, backend_parameters=None,
            ssl_cert_path=None, ssl_key_path=None):

        self.port = port
        if self.port is None:
            self.port = DEFAULT_PORT

        if backend_parameters is None:
            backend_parameters = {}

        Backend = backends.get(backend)
        if Backend is None:
            raise ConfigurationException("The '%s' backend isn't supported" % backend)
        self.backend = Backend(**backend_parameters)

        if ssl_cert_path is None or ssl_key_path is None:
            raise ConfigurationException("An SSL cert and key must be provided")

        self.pool = Pool(MAX_CONNECTIONS)
        log.debug("Starting server with SSL cert '%s' and key '%s'" % (ssl_cert_path, ssl_key_path))

        self.server = StreamServer(('', self.port), self.handle_message,
            certfile=ssl_cert_path, keyfile=ssl_key_path,
            spawn=self.pool)
        log.info("%s serving on port %s" % (__fullversion__, self.port))
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            log.info("Stopping server...")
            self.server.stop()
            log.info("Server stopped")

    def handle_message(self, sock, address):
        log.debug("Opening socket")

        while True:
            message = ''
            while True:
                bufr = sock.recv(BUF_SIZE)
                message += bufr
                if len(bufr) != BUF_SIZE:
                    break
            log.debug("Received: '%s'" % message)

            if message == '':
                break

            response = self.backend.handle(message)
            if response is not None:
                log.debug("Responded: '%s'" % response)
                sock.sendall(response)
            else:
                log.debug("Got no response from backend")
                break

        sock.close()
        log.debug("Closing socket")
