import logging

import opentsdbproxy

logging.basicConfig(level=logging.DEBUG)


def main():
    backend = "forwarding"
    backend_parameters = {'host': 'nimbus-opentsdb.no-ip.org', 'port': 4242}
    opentsdbproxy.OpenTSDBProxy(backend=backend, backend_parameters=backend_parameters)
