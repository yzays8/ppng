import sys
import os
import random
import string
import zlib

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_PATH)
from src.ppng.decompressor.zlib import Zlib

class TestDecompress:
    def test_no_compression_hello(self):
        data = b'Hello, world!'
        compressed = zlib.compress(data, level=0)
        assert Zlib().decompress_zlib(compressed) == data

    def test_no_compression_1KB(self):
        data = b'a' * 10**3
        compressed = zlib.compress(data, level=0)
        assert Zlib().decompress_zlib(compressed) == data

    def test_no_compression_1MB(self):
        data = b'a' * 10**6
        compressed = zlib.compress(data, level=0)
        assert Zlib().decompress_zlib(compressed) == data

    def test_no_compression_random(self):
        data = ''.join(random.choices(string.ascii_letters + string.digits, k=100)).encode('utf-8')
        compressed = zlib.compress(data, level=0)
        assert Zlib().decompress_zlib(compressed) == data

    def test_fixed_huffman_aaaaa(self):
        data = b'aaaaa'
        compressed = zlib.compress(data, level=1)
        assert Zlib().decompress_zlib(compressed) == data

    def test_fixed_huffman_aaabbbcccaaabbbddd(self):
        data = b'aaabbbcccaaabbbddd'
        compressed = zlib.compress(data, level=1)
        assert Zlib().decompress_zlib(compressed) == data

    def test_fixed_huffman_hello(self):
        data = b'Hello, world!'
        compressed = zlib.compress(data, level=1)
        assert Zlib().decompress_zlib(compressed) == data

    def test_fixed_huffman_1234567890(self):
        data = b'1234567890'
        compressed = zlib.compress(data, level=1)
        assert Zlib().decompress_zlib(compressed) == data

    def test_fixed_huffman_1KB(self):
        data = b'a' * 10**3
        compressed = zlib.compress(data, level=1)
        assert Zlib().decompress_zlib(compressed) == data

    def test_dynamic_huffman_1MB(self):
        data = b'a' * 10**6
        compressed = zlib.compress(data, level=9)
        assert Zlib().decompress_zlib(compressed) == data

    def test_dynamic_huffman_random(self):
        data = ''.join(random.choices(string.ascii_letters + string.digits, k=10000)).encode('utf-8')
        compressed = zlib.compress(data, level=9)
        assert Zlib().decompress_zlib(compressed) == data
