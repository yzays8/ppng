import sys
import os
import io
import random
import string
import zlib

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_PATH)
from src.pngd.decompressor import Decompressor

class TestDecompress:
    def test_no_compression_hello(self):
        decompressor = Decompressor()
        data = b'Hello, world!'
        compressed = zlib.compress(data, level=0)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_no_compression_1KB(self):
        decompressor = Decompressor()
        data = b'a' * 10**3
        compressed = zlib.compress(data, level=0)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_no_compression_1MB(self):
        decompressor = Decompressor()
        data = b'a' * 10**6
        compressed = zlib.compress(data, level=0)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_no_compression_random(self):
        decompressor = Decompressor()
        data = ''.join(random.choices(string.ascii_letters + string.digits, k=100)).encode('utf-8')
        compressed = zlib.compress(data, level=0)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_fixed_huffman_aaaaa(self):
        decompressor = Decompressor()
        data = b'aaaaa'
        compressed = zlib.compress(data, level=1)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_fixed_huffman_aaabbbcccaaabbbddd(self):
        decompressor = Decompressor()
        data = b'aaabbbcccaaabbbddd'
        compressed = zlib.compress(data, level=1)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_fixed_huffman_hello(self):
        decompressor = Decompressor()
        data = b'Hello, world!'
        compressed = zlib.compress(data, level=1)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_fixed_huffman_1234567890(self):
        decompressor = Decompressor()
        data = b'1234567890'
        compressed = zlib.compress(data, level=1)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_fixed_huffman_1KB(self):
        decompressor = Decompressor()
        data = b'a' * 10**3
        compressed = zlib.compress(data, level=1)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_dynamic_huffman_1MB(self):
        decompressor = Decompressor()
        data = b'a' * 10**6
        compressed = zlib.compress(data, level=9)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data

    def test_dynamic_huffman_random(self):
        decompressor = Decompressor()
        data = ''.join(random.choices(string.ascii_letters + string.digits, k=10000)).encode('utf-8')
        compressed = zlib.compress(data, level=9)
        assert decompressor._decompress_zlib(io.BytesIO(compressed)) == data
