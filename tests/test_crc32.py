import random
import string
import zlib

from src.ppng.decoder.crc32 import calculate_crc32


class TestCRC32:
    def test_IEND(self) -> None:
        data = "IEND".encode("utf-8")
        assert zlib.crc32(data) == calculate_crc32(data)

    def test_empty(self) -> None:
        data = b""
        assert zlib.crc32(data) == calculate_crc32(data)

    def test_123456789(self) -> None:
        data = b"123456789"
        assert zlib.crc32(data) == calculate_crc32(data)

    def test_16bytes(self) -> None:
        data = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
        assert zlib.crc32(data) == calculate_crc32(data)

    def test_utf8(self) -> None:
        data = "こんにちは世界".encode("utf-8")
        assert zlib.crc32(data) == calculate_crc32(data)

    def test_1MB(self) -> None:
        data = b"a" * 10**6
        assert zlib.crc32(data) == calculate_crc32(data)

    def test_random(self) -> None:
        data = "".join(
            random.choices(string.ascii_letters + string.digits, k=100)
        ).encode("utf-8")
        assert zlib.crc32(data) == calculate_crc32(data)
