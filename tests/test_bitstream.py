from src.ppng.utils.bitstream import BitStream


class TestBitStream:
    def test_read_bit_3F20(self) -> None:
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
        try:
            bit_stream.read_bit()
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bits_3F20(self) -> None:
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bits(8) == 0b11111100
        assert bit_stream.read_bits(8) == 0b00000100
        try:
            bit_stream.read_bits(8)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bits_3F20_not_reverse(self) -> None:
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bits(8, reverse=False) == 0x3F
        assert bit_stream.read_bits(8, reverse=False) == 0x20
        try:
            bit_stream.read_bits(8, reverse=False)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_byte_3F20(self) -> None:
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_byte() == 0b11111100
        assert bit_stream.read_byte() == 0b00000100
        try:
            bit_stream.read_byte()
        except IndexError:
            assert True
        else:
            assert False

    def test_read_byte_3F20_not_reverse(self) -> None:
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_byte(reverse=False) == 0x3F
        assert bit_stream.read_byte(reverse=False) == 0x20
        try:
            bit_stream.read_byte(reverse=False)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bytes_3F20(self) -> None:
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bytes(2) == 0b1111110000000100
        try:
            bit_stream.read_bytes(2)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bytes_3F20_not_reverse(self) -> None:
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bytes(2, reverse=False) == 0x3F20
        try:
            bit_stream.read_bytes(2, reverse=False)
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bytes_3F20_little(self) -> None:
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bytes(2, endian="little") == 0b0000010011111100
        try:
            bit_stream.read_bytes(2, endian="little")
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bytes_3F20_little_not_reverse(self) -> None:
        stream = b"\x3F\x20"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bytes(2, reverse=False, endian="little") == 0x203F
        try:
            bit_stream.read_bytes(2, reverse=False, endian="little")
        except IndexError:
            assert True
        else:
            assert False

    def test_read_bits_and_bytes_3F204A(self) -> None:
        stream = b"\x3F\x20\x4A"
        bit_stream = BitStream(stream)
        assert bit_stream.read_bits(3) == 0b111
        assert bit_stream.read_bits(2) == 0b11
        assert bit_stream.read_bytes(2) == 0b0000010001010010
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
