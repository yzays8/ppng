import io
import sys
import zlib

from loguru import logger

from .adler32 import calculate_adler32
from .utils import BitStream

class Decompressor():
    def __init__(self, is_logging: bool = False) -> None:
        logger.remove()
        logger.add(sys.stdout, filter=lambda record: is_logging)

        # If a message higher than ERROR is logged while _is_logging is False, log it to stderr regardless of the logging flag
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not is_logging)

    def _decompress_zlib(self, data: io.BytesIO) -> bytes:
        bit_stream = BitStream(data)
        self._interpret_zlib_header(*self._read_zlib_header(bit_stream))
        decompressed_data = self._decompress_deflate(bit_stream)
        adler32_checksum = bit_stream.read_bytes(4, reverse=False)
        calculated_checksum = calculate_adler32(decompressed_data)
        if adler32_checksum != calculated_checksum:
            logger.error(f'Invalid Adler-32 checksum (expected: {hex(adler32_checksum)}, actual: {hex(calculated_checksum)})')
            sys.exit(1)
        return decompressed_data

    def _read_zlib_header(self, data: BitStream) -> tuple[int, int]:
        # Big endian
        cmf = data.read_byte(reverse=False)
        flg = data.read_byte(reverse=False)
        return cmf, flg

    def _interpret_zlib_header(self, cmf: int, flg: int) -> bytes:
        if (cmf << 8 | flg) % 31 != 0:
            logger.error('Invalid zlib header')
            sys.exit(1)

        cm = cmf & 0b1111
        if cm != 8:
            logger.error(f'CM (Compression method) must be 8 for deflate compression, but got {cm}')
            sys.exit(1)

        cinfo = (cmf >> 4) & 0b1111
        if cinfo > 7:
            logger.error(f'CINFO (Compression info) must be less than or equal to 7, but got {cinfo}')
            sys.exit(1)

        # fcheck = flg & 0b11111

        fdict = (flg >> 5) & 0b1
        if fdict:
            logger.error('A preset dictionary is not supported')
            sys.exit(1)

        # The information in FLEVEL is not needed for decompression.
        flevel = (flg >> 6) & 0b11
        match flevel:
            case 0:
                logger.info('Compression level: fastest')
            case 1:
                logger.info('Compression level: fast')
            case 2:
                logger.info('Compression level: default')
            case 3:
                logger.info('Compression level: maximum, slowest')
            case _:
                assert False

    def _decompress_deflate(self, data_stream: BitStream) -> bytes:
        output = io.BytesIO()

        while True:
            # Read the header of the deflate block
            bfinal = data_stream.read_bit()
            btype = data_stream.read_bits(2, reverse=False)

            match btype:
                case 0b00:
                    # No compression
                    len = data_stream.read_bytes(2, reverse=False, endian='little')
                    nlen = data_stream.read_bytes(2, reverse=False, endian='little')
                    if len != (~nlen & 0xFFFF):
                        logger.error('NLEN is not the one\'s complement of LEN')
                        sys.exit(1)
                    output.write(data_stream.read_bytes(len, reverse=False).to_bytes(len))
                case 0b01:
                    # Compressed with fixed Huffman codes

                    # Read remaining bits in the deflate block header and make a Huffman code up to 5 bits
                    huffman_code = data_stream.read_bits(5)
                    huffman_code_length = 5

                    # Read the compressed data
                    while True:
                        huffman_code = (huffman_code << 1) | data_stream.read_bit()
                        huffman_code_length += 1

                        if huffman_code_length == 7:
                            if huffman_code in range(0b0000000, 0b0010111 + 1):
                                # Decoded value is between 256 - 279
                                decoded_value = huffman_code - 0b0000000 + 256
                                # End of block
                                if decoded_value == 256:
                                    break
                                self._decode_LZ77(data_stream, decoded_value, output)
                                huffman_code_length = 0
                                huffman_code = 0
                            else:
                                pass
                        elif huffman_code_length == 8:
                            if huffman_code in range(0b00110000, 0b10111111 + 1):
                                # Decoded value is between 0 - 143
                                decoded_value = huffman_code - 0b00110000 + 0
                                output.write(decoded_value.to_bytes(1))
                                huffman_code_length = 0
                                huffman_code = 0
                            elif huffman_code in range(0b11000000, 0b11000111 + 1):
                                # Decoded value is between 280 - 287
                                decoded_value = huffman_code - 0b11000000 + 280
                                self._decode_LZ77(data_stream, decoded_value, output)
                                huffman_code_length = 0
                                huffman_code = 0
                            else:
                                pass
                        elif huffman_code_length == 9:
                            if huffman_code in range(0b110010000, 0b111111111 + 1):
                                # Decoded value is between 144 - 255
                                decoded_value = huffman_code - 0b110010000 + 144
                                output.write(decoded_value.to_bytes(1))
                                huffman_code_length = 0
                                huffman_code = 0
                            else:
                                logger.error(f'Invalid Huffman code: {bin(huffman_code)}')
                                sys.exit(1)
                        elif huffman_code_length > 9:
                            assert False
                        else:
                            pass
                case 0b10:
                    # Compressed with dynamic Huffman codes
                    logger.error('Dynamic Huffman codes are not implemented')
                    sys.exit(1)
                case 0b11:
                    logger.error('BTYPE 0b11 is reserved for future use')
                    sys.exit(1)
                case _:
                    assert False

            if bfinal:
                break

        return output.getvalue()

    def _decode_LZ77(self, input_stream: BitStream, value: int, output_stream: io.BytesIO) -> None:
        # Get the length of the match
        if value in range(257, 264 + 1):
            relative_length = 3 + value - 257
            extra_bits_length = 0
        elif value in range(265, 268 + 1):
            relative_length = 11 + 2 * (value - 265)
            extra_bits_length = 1
        elif value in range(269, 272 + 1):
            relative_length = 19 + 4 * (value - 269)
            extra_bits_length = 2
        elif value in range(273, 276 + 1):
            relative_length = 35 + 8 * (value - 273)
            extra_bits_length = 3
        elif value in range(277, 280 + 1):
            relative_length = 67 + 16 * (value - 277)
            extra_bits_length = 4
        elif value in range(281, 284 + 1):
            relative_length = 131 + 32 * (value - 281)
            extra_bits_length = 5
        elif value == 285:
            relative_length = 258
            extra_bits_length = 0
        else:
            logger.error(f'Invalid decoded value: {value}')
            sys.exit(1)
        extra_bits = input_stream.read_bits(extra_bits_length, reverse=False)
        length = relative_length + extra_bits

        # Get the distance of the match
        # dist_code is 5 bits long and should be read in reverse order same as the Huffman code
        dist_code = input_stream.read_bits(5)
        if dist_code in range(0, 3 + 1):
            relative_distance = dist_code + 1
            extra_bits_length = 0
        elif dist_code in range(4, 5 + 1):
            relative_distance = 5 + 2 * (dist_code - 4)
            extra_bits_length = 1
        elif dist_code in range(6, 7 + 1):
            relative_distance = 9 + 4 * (dist_code - 6)
            extra_bits_length = 2
        elif dist_code in range(8, 9 + 1):
            relative_distance = 17 + 8 * (dist_code - 8)
            extra_bits_length = 3
        elif dist_code in range(10, 11 + 1):
            relative_distance = 33 + 16 * (dist_code - 10)
            extra_bits_length = 4
        elif dist_code in range(12, 13 + 1):
            relative_distance = 65 + 32 * (dist_code - 12)
            extra_bits_length = 5
        elif dist_code in range(14, 15 + 1):
            relative_distance = 129 + 64 * (dist_code - 14)
            extra_bits_length = 6
        elif dist_code in range(16, 17 + 1):
            relative_distance = 257 + 128 * (dist_code - 16)
            extra_bits_length = 7
        elif dist_code in range(18, 19 + 1):
            relative_distance = 513 + 256 * (dist_code - 18)
            extra_bits_length = 8
        elif dist_code in range(20, 21 + 1):
            relative_distance = 1025 + 512 * (dist_code - 20)
            extra_bits_length = 9
        elif dist_code in range(22, 23 + 1):
            relative_distance = 2049 + 1024 * (dist_code - 22)
            extra_bits_length = 10
        elif dist_code in range(24, 25 + 1):
            relative_distance = 4097 + 2048 * (dist_code - 24)
            extra_bits_length = 11
        elif dist_code in range(26, 27 + 1):
            relative_distance = 8193 + 4096 * (dist_code - 26)
            extra_bits_length = 12
        elif dist_code in range(28, 29 + 1):
            relative_distance = 16385 + 8192 * (dist_code - 28)
            extra_bits_length = 13
        else:
            logger.error(f'Invalid distance code: {dist_code}')
            sys.exit(1)
        extra_bits = input_stream.read_bits(extra_bits_length, reverse=False)
        distance = relative_distance + extra_bits

        # Copy the match to the output
        for _ in range(length):
            output_stream.write(output_stream.getvalue()[-distance].to_bytes(1))

    def decompress(self, data: io.BytesIO) -> bytes:
        decompressor = zlib.decompressobj()
        decompressed_data = decompressor.decompress(data.getbuffer())
        return decompressed_data
