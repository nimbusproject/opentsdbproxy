from gevent import socket
from gevent.server import StreamServer

__version__ = "0.1"
__fullversion__ = "OpenTSDB Proxy %s" % __version__


class OpenTSDBProxy(object):

    def __init__(self):

        self.port = 4242
        self.opentsdb_host = "nimbus-opentsdb.no-ip.org"
        self.opentsdb_port = 4242

        self.server = StreamServer(('', self.port), self.handle_metric)
        self.server.serve_forever()

    def handle_metric(self, sock, address):
        fp = sock.makefile()
        while True:
            line = fp.readline()
            if line == "version\n":
                msg = "%s" % __fullversion__
                print msg
                fp.write(msg)
                fp.flush()
            else:
                print "unknown '%s'" % line
                break

        sock.shutdown(socket.SHUT_WR)
        sock.close()
