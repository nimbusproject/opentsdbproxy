import os
import sys
import logging
import argparse

import opentsdbproxy

from opentsdbproxy.exceptions import ConfigurationException

logging.basicConfig(level=logging.DEBUG)


def main():

    parser = argparse.ArgumentParser(description=opentsdbproxy.__fullversion__)
    parser.add_argument('--backend', metavar='mock', default='mock', type=str,
        help="Choose from 'mock', 'forwarding', 'django_authz'")
    parser.add_argument('--port', metavar='4242', type=int, default=4242,
        help="Port to listen to tcollector messages")
    parser.add_argument('--ssl-cert', metavar='server.crt', required=True,
        help="SSL Certificate")
    parser.add_argument('--ssl-key', metavar='server.key', required=True,
        help="SSL Key")
    parser.add_argument('--opentsdb-host', metavar='example.com',
        help="Host to forward messages to, used by 'forwarding' and 'django_authz'")
    parser.add_argument('--opentsdb-port', default=4242,
        help="Port of host to forward messages to, used by 'forwarding' and 'django_authz'")
    parser.add_argument('--django-project-path',
        help="Path to the Django project you would like to authz against, used by 'django_authz'")
    parser.add_argument('--django-settings-module',
        help="The settings module of your Django project, used by 'django_authz'")

    args = parser.parse_args()

    backend = args.backend.lower()
    backend_parameters = {}

    if backend == 'forwarding':
        backend_parameters = {'host': args.opentsdb_host, 'port': args.opentsdb_port}
    elif backend in ('django_authz', 'mock_django_authz',):
        backend_parameters = {
            'host': args.opentsdb_host, 'port': args.opentsdb_port,
            'django_project_path': args.django_project_path,
            'django_settings_module': args.django_settings_module
        }
    ssl_cert_path = os.path.abspath(os.path.expanduser(args.ssl_cert))
    ssl_key_path = os.path.abspath(os.path.expanduser(args.ssl_key))

    try:
        opentsdbproxy.OpenTSDBProxy(backend=backend, backend_parameters=backend_parameters,
            ssl_cert_path=ssl_cert_path, ssl_key_path=ssl_key_path, port=args.port)
    except ConfigurationException as ce:
        print >>sys.stderr, "Configuration Error: %s" % str(ce)
