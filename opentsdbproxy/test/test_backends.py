import os
import time
import uuid

import opentsdbproxy

from random import choice
from nose.plugins.skip import SkipTest
from unittest import TestCase

from opentsdbproxy.backends import MockOpenTSDBBackend, ForwardingOpenTSDBBackend

OPENTSDB_BUILT_STRING = "net.opentsdb built at revision"


class TestMockOpenTSDBBackend(TestCase):

    def setUp(self):

        self.backend = MockOpenTSDBBackend()

    def test_messages(self):

        msg = "version\n"
        response = self.backend.handle(msg)

        self.assertEqual(response, "%s\n" % opentsdbproxy.__version__)

        msg = "put test.my.value 1366155625 42 host=bandersnatch.phys.uvic.ca password=pencil user=joshua\n"
        response = self.backend.handle(msg)

        self.assertIsNone(response)
        self.assertIn(msg, self.backend.messages)


class TestForwardingOpenTSDBBackend(TestCase):

    def setUp(self):

        self.opentsdb_host = os.environ.get('OPENTSDB_HOST')
        self.opentsdb_port = os.environ.get('OPENTSDB_PORT')

        if self.opentsdb_host is None or self.opentsdb_port is None:
            raise SkipTest("OPENTSDB_HOST and OPENTSDB_PORT must be set for OpenTSDB backed tests")

        self.backend = ForwardingOpenTSDBBackend(host=self.opentsdb_host, port=self.opentsdb_port)

    def test_messages(self):
        msg = "version\n"
        response = self.backend.handle(msg)
        self.assertIn(OPENTSDB_BUILT_STRING, response)

        now = int(time.time())
        metric = "test.my.value"
        value = choice(range(0, 42))
        unique_tag = uuid.uuid4().hex

        msg = "put %s %s %s uuid=%s" % (metric, now, value, unique_tag)
        response = self.backend.handle(msg)
        print msg
        time.sleep(1)
        self.assertIsNone(response)

        assert False
