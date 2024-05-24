import io
import sys

class BitStream:
    def __init__(self, byte_stream: bytes) -> None:
        self.stream = io.BytesIO(byte_stream)
        self.byte = 0
        self.bit_offset = 0

    # Returns 1 bit from the data sliced byte by byte from the stream.
    # The bit is read from the LSB to the MSB of the byte.
    def read_bit(self) -> int:
        if self.bit_offset == 0:
            self.byte = self.stream.read(1)[0]
        bit = self.byte & 0b1
        self.byte >>= 1
        self.bit_offset += 1
        if self.bit_offset == 8:
            self.bit_offset = 0
        return bit

    # e.g. 0b01001011 -> 0b11010010 (reverse=True)
    def read_bits(self, length: int, reverse: bool = True) -> int:
        bits = 0
        if reverse:
            for _ in range(length):
                bits = (bits << 1) | self.read_bit()
        else:
            for i in range(length):
                bits |= self.read_bit() << i
        return bits

    # If the position of the bit is not a multiple of 8, ignore the remaining bits and read the next byte.
    def read_byte(self, reverse: bool = True) -> int:
        if self.bit_offset != 0:
            self.bit_offset = 0
        self.byte = self.stream.read(1)[0]
        if reverse == False:
            return self.byte
        return int('{:08b}'.format(self.byte)[::-1], 2)

    def read_bytes(self, length: int, reverse: bool = True, endian: str = 'big') -> int:
        ret = 0
        match endian:
            case 'big':
                for _ in range(length):
                    ret = (ret << 8) | self.read_byte(reverse=reverse)
            case 'little':
                for i in range(length):
                    ret |= self.read_byte(reverse=reverse) << (8 * i)
            case _:
                print('Invalid endian type. Specify "big" or "little".')
                sys.exit(1)
        return ret
