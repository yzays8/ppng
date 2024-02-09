import sys
import os
import random
import string
import zlib

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_PATH)
from src.pngd.adler32 import calculate_adler32

class TestAdler32:
    def _assert_equal_adler32(self, data: bytes) -> None:
        assert zlib.adler32(data) == calculate_adler32(data)

    def test_empty(self):
        self._assert_equal_adler32(b'')

    def test_123456789(self):
        self._assert_equal_adler32(b'123456789')

    def test_16bytes(self):
        self._assert_equal_adler32(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')

    def test_utf8(self):
        self._assert_equal_adler32('こんにちは世界'.encode('utf-8'))

    def test_1MB(self):
        self._assert_equal_adler32(b'a' * 10**6)

    def test_random(self):
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
        self._assert_equal_adler32(random_string.encode('utf-8'))
