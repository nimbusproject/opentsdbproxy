import os
import sys
import socket
import logging

import opentsdbproxy

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
            return "%s\n" % opentsdbproxy.__version__
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
        log.debug("Forwarding: '%s'" % message)
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


class DjangoMixin(object):

    django_setup = False

    def setup_django(self, django_project_path, django_settings_module):
        sys.path.append(django_project_path)  # TODO: check path exists
        os.environ['DJANGO_SETTINGS_MODULE'] = django_settings_module
        self.django_setup = True

        from django.contrib.auth.models import User
        from django.contrib.auth import authenticate
        self.User = User
        self.authenticate = authenticate

    def filter_message(self, message):
        """Checks each line in a tcollector message for user and password,
        rejects messages without a valid username and password. Returns a
        tcollector message with the unauth'd lines removed.
        """
        cached_authed_pairs = {}
        authzed_lines = []

        for line in message.splitlines():
            user = None
            password = None
            items = line.split()
            for tag in items:
                split_tag = tag.split('=', 1)
                if len(split_tag) != 2:
                    continue
                key, value = split_tag
                if key == 'user':
                    user = value
                elif key == 'password':
                    password = value

            cached_auth = cached_authed_pairs.get((user, password))
            if cached_auth is not None:
                auth = cached_auth
            else:
                auth = self.authenticate(username=user, password=password)
                cached_authed_pairs[(user, password)] = auth

            if auth is not None:

                # Sanitize password
                password_tag = "password=%s" % password
                line = line.replace(password_tag, '')

                authzed_lines.append(line.strip())

        return '\n'.join(authzed_lines) + '\n'  # Add trailing \n because tcollector does


class DjangoAuthorizingBackend(ForwardingOpenTSDBBackend, DjangoMixin):
    def __init__(self, host=None, port=None, django_project_path=None, django_settings_module=None):
        if django_project_path is None or django_settings_module is None:
            raise ConfigurationException(
                "%s requires a django_settings_module and django_project_path to be configured" % (
                self.__class__.__name__,))

        self.setup_django(django_project_path, django_settings_module)

        ForwardingOpenTSDBBackend.__init__(self, host=host, port=port)

    def handle(self, message):

        if message == "version\n":
            filtered_message = message
        else:
            filtered_message = self.filter_message(message)

        log.debug("Filtered message to: %s" % filtered_message)
        if filtered_message != '\n':
            return ForwardingOpenTSDBBackend.handle(self, filtered_message)
        else:
            return None


class MockDjangoAuthorizingBackend(MockOpenTSDBBackend, DjangoMixin):

    def __init__(self, host=None, port=None, django_project_path=None, django_settings_module=None):
        if django_project_path is None or django_settings_module is None:
            raise ConfigurationException(
                "%s requires a django_settings_module and django_project_path to be configured" % (
                self.__class__.__name__,))

        self.setup_django(django_project_path, django_settings_module)

        self.messages = []
        self.authzed_messages = []

    def handle(self, message):

        self.messages.append(message)
        log.debug("MockDjangoAuthorizingBackend got message: '%s'" % message)

        if message == "version\n":
            return "%s\n" % opentsdbproxy.__version__
        else:
            filtered_message = self.filter_message(message)
            log.debug("Filtered Message: '%s'" % filtered_message)
            if filtered_message != '\n':
                self.authzed_messages.append(filtered_message)

    def reset(self):
        self.messages = []
        self.authzed_messages = []


backends = {
    'mock': MockOpenTSDBBackend,
    'forwarding': ForwardingOpenTSDBBackend,
    'django_authz': DjangoAuthorizingBackend,
    'mock_django_authz': MockDjangoAuthorizingBackend,
}
