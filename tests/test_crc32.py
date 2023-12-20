import sys
import os
import random
import string
import zlib

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_PATH)
from src.pngd.crc32 import calculate_crc32

def assert_crc32(data: bytes) -> None:
    expected = zlib.crc32(data)
    actual = calculate_crc32(data)
    if expected != actual:
        raise AssertionError(f'Invalid CRC32 (expected: {hex(expected)}, actual: {hex(actual)})')

def test_crc32():
    try:
        assert_crc32('IEND'.encode('utf-8'))
        assert_crc32(b'')
        assert_crc32(b'123456789')
        assert_crc32(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')
        assert_crc32('こんにちは世界'.encode('utf-8'))
        assert_crc32(b'a' * 10**6)
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
        assert_crc32(random_string.encode('utf-8'))
    except AssertionError as e:
        print(f'Failed: {e}')
        return

if __name__ == '__main__':
    test_crc32()
