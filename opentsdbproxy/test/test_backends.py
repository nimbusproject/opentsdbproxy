import os
import time
import uuid
import urllib
import httplib

import opentsdbproxy

from random import choice
from nose.plugins.skip import SkipTest
from unittest import TestCase

from opentsdbproxy.backends import MockOpenTSDBBackend,\
    ForwardingOpenTSDBBackend, MockDjangoAuthorizingBackend, DjangoAuthorizingBackend

OPENTSDB_BUILT_STRING = "net.opentsdb built at revision"
DJANGO_PROJECT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
    "django_test_project")
DJANGO_SETTINGS_MODULE = "testproject.settings"


def query_opentsdb(host, port, m):
    start = "1m-ago"

    params = urllib.urlencode({
        'm': m,
        'start': start,
        'ascii': 'true',
    })
    connection = httplib.HTTPConnection(host, port)
    connection.request('GET', '/q?%s' % params)
    return connection.getresponse()


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

        msg = "put %s %s %s uuid=%s\n" % (metric, now, value, unique_tag)
        response = self.backend.handle(msg)

        # Wait 1s for a response
        time.sleep(1)
        self.assertIsNone(response)

        # Check that our value got put into OpenTSDB
        m = "avg:%s{uuid=%s}" % (metric, unique_tag)

        response = query_opentsdb(self.opentsdb_host, self.opentsdb_port, m)
        self.assertEqual(200, response.status)
        read_response = response.read()

        read_metric, ts, read_value, read_tag = read_response.split()

        self.assertEqual(read_metric, metric)
        self.assertEqual(read_value, str(value))
        self.assertEqual(read_tag, "uuid=%s" % unique_tag)


class TestMockDjangoAuthorizingBackend(TestCase):

    def setUp(self):

        self.backend = MockDjangoAuthorizingBackend(
            django_project_path=DJANGO_PROJECT_DIR,
            django_settings_module=DJANGO_SETTINGS_MODULE
        )

    def test_messages(self):
        msg = "version\n"
        response = self.backend.handle(msg)
        self.assertEqual(response, "%s\n" % opentsdbproxy.__version__)

        # Make sure messages with no username/password don't get through
        msg = "put test.my.value 1366155625 42 host=bandersnatch.phys.uvic.ca\n"
        response = self.backend.handle(msg)
        self.assertIsNone(response)
        self.assertIn(msg, self.backend.messages)
        self.assertEqual(0, len(self.backend.authzed_messages))

        self.backend.reset()

        # Make sure messages with bad username/password don't get through
        msg = "put test.my.value 1366155625 42 host=bandersnatch.phys.uvic.ca user=%s password=%s\n"
        msg = msg % ("joshua", "pencil")
        response = self.backend.handle(msg)
        self.assertIsNone(response)
        self.assertIn(msg, self.backend.messages)
        self.assertEqual(0, len(self.backend.authzed_messages))

        self.backend.reset()

        # Make sure messages with good username and bad password don't get through
        msg = "put test.my.value 1366155625 42 host=bandersnatch.phys.uvic.ca user=%s password=%s\n"
        msg = msg % ("root", "pencil")
        response = self.backend.handle(msg)
        self.assertIsNone(response)
        self.assertIn(msg, self.backend.messages)
        self.assertEqual(0, len(self.backend.authzed_messages))

        self.backend.reset()

        # Make sure messages with good username and no password don't get through
        msg = "put test.my.value 1366155625 42 host=bandersnatch.phys.uvic.ca user=%s\n"
        msg = msg % "root"
        response = self.backend.handle(msg)
        self.assertIsNone(response)
        self.assertIn(msg, self.backend.messages)
        self.assertEqual(0, len(self.backend.authzed_messages))

        self.backend.reset()

        # Make sure messages with good username and good password get through
        msg = "put test.my.value 1366155625 42 host=bandersnatch.phys.uvic.ca user=%s password=%s\n"
        msg = msg % ("root", "root")
        response = self.backend.handle(msg)
        self.assertIsNone(response)
        self.assertIn(msg, self.backend.messages)
        msg_password_stripped = msg.replace(' password=root', '')
        self.assertIn(msg_password_stripped, self.backend.authzed_messages)

        self.backend.reset()

        # Make sure messages with two parts and good username and good password get through
        msg = "put test.my.value 1366155625 42 host=bandersnatch.phys.uvic.ca user=%s password=%s\n"
        msg += "put test.my.value 1366155635 42 host=bandersnatch.phys.uvic.ca user=%s password=%s\n"
        msg = msg % ("root", "root", "root", "root")
        response = self.backend.handle(msg)
        self.assertIsNone(response)
        self.assertIn(msg, self.backend.messages)

        msg_password_stripped = msg.replace(' password=root', '')
        self.assertIn(msg_password_stripped, self.backend.authzed_messages)

        self.backend.reset()

        # Make sure messages with some auth lines and some not auth lines are
        # handled appropriately
        good_msg = "put test.my.value 1366155625 42 host=bandersnatch.phys.uvic.ca user=%s password=%s\n" % (
            "root", "root")
        bad_msg = "put test.my.value 1366155635 42 host=bandersnatch.phys.uvic.ca user=%s password=%s\n" % (
            "root", "bad")
        msg = good_msg + bad_msg
        response = self.backend.handle(msg)
        self.assertIsNone(response)
        self.assertIn(msg, self.backend.messages)

        good_msg_password_stripped = good_msg.replace(' password=root', '')
        self.assertIn(good_msg_password_stripped, self.backend.authzed_messages)


class TestDjangoAuthorizingBackend(TestCase):

    def setUp(self):

        self.opentsdb_host = os.environ.get('OPENTSDB_HOST')
        self.opentsdb_port = os.environ.get('OPENTSDB_PORT')

        if self.opentsdb_host is None or self.opentsdb_port is None:
            raise SkipTest("OPENTSDB_HOST and OPENTSDB_PORT must be set for OpenTSDB backed tests")

        self.backend = DjangoAuthorizingBackend(
            host=self.opentsdb_host,
            port=self.opentsdb_port,
            django_project_path=DJANGO_PROJECT_DIR,
            django_settings_module=DJANGO_SETTINGS_MODULE
        )

    def test_messages(self):
        msg = "version\n"
        response = self.backend.handle(msg)
        self.assertIn(OPENTSDB_BUILT_STRING, response)

        now = int(time.time())
        metric = "test.my.value"
        value = choice(range(0, 42))
        good_username = "root"
        good_password = "root"
        bad_username = "joshua"
        bad_password = "pencil"

        # Ensure that messages with no u/p are filtered
        unique_tag = uuid.uuid4().hex
        msg = "put %s %s %s uuid=%s\n" % (metric, now, value, unique_tag)
        response = self.backend.handle(msg)

        time.sleep(1)
        self.assertIsNone(response)

        m = "avg:%s{uuid=%s}" % (metric, unique_tag)
        response = query_opentsdb(self.opentsdb_host, self.opentsdb_port, m)
        self.assertEqual(400, response.status)

        # Ensure that messages with bad u/p are filtered
        unique_tag = uuid.uuid4().hex
        msg = "put %s %s %s uuid=%s user=%s password=%s\n" % (
            metric, now, value, unique_tag, bad_username, bad_password)
        response = self.backend.handle(msg)

        time.sleep(1)
        self.assertIsNone(response)

        m = "avg:%s{uuid=%s}" % (metric, unique_tag)
        response = query_opentsdb(self.opentsdb_host, self.opentsdb_port, m)
        self.assertEqual(400, response.status)

        # Ensure that messages with good u bad p are filtered
        unique_tag = uuid.uuid4().hex
        msg = "put %s %s %s uuid=%s user=%s password=%s\n" % (
            metric, now, value, unique_tag, good_username, bad_password)
        response = self.backend.handle(msg)

        time.sleep(1)
        self.assertIsNone(response)

        m = "avg:%s{uuid=%s}" % (metric, unique_tag)
        response = query_opentsdb(self.opentsdb_host, self.opentsdb_port, m)
        self.assertEqual(400, response.status)

        # Ensure that messages with good u no p are filtered
        unique_tag = uuid.uuid4().hex
        msg = "put %s %s %s uuid=%s user=%s\n" % (
            metric, now, value, unique_tag, good_username)
        response = self.backend.handle(msg)

        time.sleep(1)
        self.assertIsNone(response)

        m = "avg:%s{uuid=%s}" % (metric, unique_tag)
        response = query_opentsdb(self.opentsdb_host, self.opentsdb_port, m)
        self.assertEqual(400, response.status)

        # Ensure that messages with good u good p are passed through
        unique_tag = uuid.uuid4().hex
        msg = "put %s %s %s uuid=%s user=%s password=%s\n" % (
            metric, now, value, unique_tag, good_username, good_password)
        response = self.backend.handle(msg)

        time.sleep(1)
        self.assertIsNone(response)

        m = "avg:%s{uuid=%s}" % (metric, unique_tag)
        response = query_opentsdb(self.opentsdb_host, self.opentsdb_port, m)
        self.assertEqual(200, response.status)

        read_response = response.read()
        read_metric, ts, read_value, read_tag = read_response.split(" ", 3)

        self.assertEqual(read_metric, metric)
        self.assertEqual(read_value, str(value))
        self.assertIn("uuid=%s" % unique_tag, read_tag)
        self.assertIn("user=%s" % good_username, read_tag)
