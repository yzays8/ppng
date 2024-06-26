import io
import os
import sys

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_PATH)
from src.ppng.utils.bitstream import BitStream


class TestBitStream:
    def test_read_bit_3F20(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bit() == 1
        assert bit_stream.read_bit() == 1
        assert bit_stream.read_bit() == 1
        assert bit_stream.read_bit() == 1
        assert bit_stream.read_bit() == 1
        assert bit_stream.read_bit() == 1
        assert bit_stream.read_bit() == 0
        assert bit_stream.read_bit() == 0
        assert bit_stream.read_bit() == 0
        assert bit_stream.read_bit() == 0
        assert bit_stream.read_bit() == 0
        assert bit_stream.read_bit() == 0
        assert bit_stream.read_bit() == 0
        assert bit_stream.read_bit() == 1
        assert bit_stream.read_bit() == 0
        assert bit_stream.read_bit() == 0
        # catch index error
        try:
            bit_stream.read_bit()
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bits_3F20(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bits(8) == 0b11111100
        assert bit_stream.read_bits(8) == 0b00000100
        # catch index error
        try:
            bit_stream.read_bits(8)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bits_3F20_not_reverse(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bits(8, reverse=False) == 0x3F
        assert bit_stream.read_bits(8, reverse=False) == 0x20
        # catch index error
        try:
            bit_stream.read_bits(8, reverse=False)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_byte_3F20(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_byte() == 0b11111100
        assert bit_stream.read_byte() == 0b00000100
        # catch index error
        try:
            bit_stream.read_byte()
        except IndexError:
            assert True
        else:
            assert False

    def test_read_byte_3F20_not_reverse(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_byte(reverse=False) == 0x3F
        assert bit_stream.read_byte(reverse=False) == 0x20
        # catch index error
        try:
            bit_stream.read_byte(reverse=False)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bytes_3F20(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bytes(2) == 0b1111110000000100
        # catch index error
        try:
            bit_stream.read_bytes(2)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bytes_3F20_not_reverse(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bytes(2, reverse=False) == 0x3F20
        # catch index error
        try:
            bit_stream.read_bytes(2, reverse=False)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bytes_3F20_little(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bytes(2, endian="little") == 0b0000010011111100
        # catch index error
        try:
            bit_stream.read_bytes(2, endian="little")
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bytes_3F20_little_not_reverse(self):
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bytes(2, reverse=False, endian="little") == 0x203F
        # catch index error
        try:
            bit_stream.read_bytes(2, reverse=False, endian="little")
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bits_and_bytes_3F204A(self):
        stream = b"\x3F\x20\x4A"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bits(3) == 0b111
        assert bit_stream.read_bits(2) == 0b11
        assert bit_stream.read_bytes(2) == 0b0000010001010010
        # catch index error
        try:
            bit_stream.read_bits(8)
        except IndexError:
            assert True
        else:
            assert False

        try:
            bit_stream.read_bytes(1)
        except IndexError:
            assert True
        else:
            assert False
