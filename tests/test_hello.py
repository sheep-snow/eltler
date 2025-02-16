import unittest

from src.hello import get_message, handler


class TestHello(unittest.TestCase):
    expected_message: str = None

    def setUp(self):
        self.expected_message = "Hello from testcode!"

    def test_handler(self):
        self.assertLogs(handler(None, None), self.expected_message)

    def test_get_message(self):
        self.assertEqual(get_message(), self.expected_message)
