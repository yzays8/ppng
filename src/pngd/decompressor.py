import io
import sys

from loguru import logger

from .adler32 import calculate_adler32
from .utils import BitStream
from . import tree

class Decompressor():
    def __init__(self, is_logging: bool = False) -> None:
        logger.remove()
        logger.add(sys.stdout, filter=lambda record: is_logging)

        # If a message higher than ERROR is logged while _is_logging is False, log it to stderr regardless of the logging flag
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not is_logging)

        self.FIXED_HUFFMAN_TREE = self._make_fixed_huffman_tree()

    def _decompress_zlib(self, data: bytes) -> bytes:
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

    def _make_fixed_huffman_tree(self) -> tree.HuffmanTree:
        huffman_tree = tree.HuffmanTree()
        for value in range(0, 143 + 1):
            huffman_tree.insert(value, 0b00110000 + value, 8)
        for value in range(144, 255 + 1):
            huffman_tree.insert(value, 0b110010000 + value - 144, 9)
        for value in range(256, 279 + 1):
            huffman_tree.insert(value, 0b0000000 + value - 256, 7)
        for value in range(280, 287 + 1):
            huffman_tree.insert(value, 0b11000000 + value - 280, 8)
        return huffman_tree

    def _read_deflate_header(self, data: BitStream) -> tuple[bool, int]:
        bfinal = data.read_bit()
        btype = data.read_bits(2, reverse=False)
        return bfinal, btype

    def _decompress_deflate(self, data_stream: BitStream) -> bytes:
        output = io.BytesIO()

        while True:
            bfinal, btype = self._read_deflate_header(data_stream)

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

                        decoded_value = self._decode_fixed_huffman_code(huffman_code, huffman_code_length)
                        if decoded_value is None:
                            continue
                        elif decoded_value in range(0, 255 + 1):
                            output.write(decoded_value.to_bytes(1))
                            huffman_code_length = 0
                            huffman_code = 0
                        elif decoded_value in range(257, 285 + 1):
                            self._decode_LZ77(data_stream, decoded_value, output)
                            huffman_code_length = 0
                            huffman_code = 0
                        elif decoded_value == 256:
                            break
                        else:
                            # 286 and 287 are included in the fixed Huffman code table, but they don't appear in the compressed data.
                            logger.error(f'Invalid Huffman code: {bin(huffman_code)}')
                            sys.exit(1)
                case 0b10:
                    # Compressed with dynamic Huffman codes

                    hlit = data_stream.read_bits(5, reverse=False)  # Number of literal/length codes - 257
                    hdist = data_stream.read_bits(5, reverse=False) # Number of distance codes - 1
                    hclen = data_stream.read_bits(4, reverse=False) # Number of code length codes - 4
                    # assert False, (hlit, hdist, hclen)

                    # Create the code length table for the code length table
                    code_length_table = {}
                    CODE_LENGTH_TABLE_INDEXES = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
                    for i in range(hclen + 4):
                        code_length_table[CODE_LENGTH_TABLE_INDEXES[i]] = data_stream.read_bits(3, reverse=False)
                    for i in range(19):
                        if i not in code_length_table:
                            code_length_table[i] = 0
                    # assert False, code_length_table
                    code_length_huffman_tree = tree.make_canonical_huffman_tree(code_length_table)

                    # Create the literal/length table and huffman tree
                    literal_length_table = {}
                    i = 0
                    while i < hlit + 257:
                        huffman_code, huffman_code_length = 0, 0
                        while True:
                            huffman_code = (huffman_code << 1) | data_stream.read_bit()
                            huffman_code_length += 1
                            decoded_value = code_length_huffman_tree.search(huffman_code, huffman_code_length)
                            if decoded_value is None:
                                continue
                            elif decoded_value == 16:
                                # Repeat previous value 3-6 times
                                extra_bits = data_stream.read_bits(2, reverse=False)
                                for _ in range(3 + extra_bits):
                                    literal_length_table[i] = literal_length_table[i - 1]
                                    i += 1
                            elif decoded_value == 17:
                                # Repeat 0 for 3-10 times
                                extra_bits = data_stream.read_bits(3, reverse=False)
                                for _ in range(3 + extra_bits):
                                    literal_length_table[i] = 0
                                    i += 1
                            elif decoded_value == 18:
                                # Repeat 0 for 11-138 times
                                extra_bits = data_stream.read_bits(7, reverse=False)
                                for _ in range(11 + extra_bits):
                                    literal_length_table[i] = 0
                                    i += 1
                            else:
                                literal_length_table[i] = decoded_value
                                i += 1
                            break

                    literal_length_huffman_tree = tree.make_canonical_huffman_tree(literal_length_table)

                    # Create the distance table and huffman tree
                    distance_table = {}
                    i = 0
                    while i < hdist + 1:
                        huffman_code, huffman_code_length = 0, 0
                        while True:
                            huffman_code = (huffman_code << 1) | data_stream.read_bit()
                            huffman_code_length += 1
                            decoded_value = code_length_huffman_tree.search(huffman_code, huffman_code_length)
                            if decoded_value is None:
                                continue
                            elif decoded_value == 16:
                                # Repeat previous value 3-6 times
                                extra_bits = data_stream.read_bits(2, reverse=False)
                                for _ in range(3 + extra_bits):
                                    distance_table[i] = distance_table[i - 1]
                                    i += 1
                            elif decoded_value == 17:
                                # Repeat 0 for 3-10 times
                                extra_bits = data_stream.read_bits(3, reverse=False)
                                for _ in range(3 + extra_bits):
                                    distance_table[i] = 0
                                    i += 1
                            elif decoded_value == 18:
                                # Repeat 0 for 11-138 times
                                extra_bits = data_stream.read_bits(7, reverse=False)
                                for _ in range(11 + extra_bits):
                                    distance_table[i] = 0
                                    i += 1
                            else:
                                distance_table[i] = decoded_value
                                i += 1
                            break

                    distance_huffman_tree = tree.make_canonical_huffman_tree(distance_table)
                    # assert False, (literal_length_huffman_tree.get_symbol_code_table(), distance_huffman_tree.get_symbol_code_table())

                    # Read the compressed data
                    huffman_code, huffman_code_length = 0, 0
                    while True:
                        huffman_code = (huffman_code << 1) | data_stream.read_bit()
                        huffman_code_length += 1

                        decoded_value = literal_length_huffman_tree.search(huffman_code, huffman_code_length)
                        if decoded_value is None:
                            continue
                        elif decoded_value in range(0, 255 + 1):
                            output.write(decoded_value.to_bytes(1))
                            huffman_code_length = 0
                            huffman_code = 0
                        elif decoded_value in range(257, 285 + 1):
                            self._decode_LZ77(data_stream, decoded_value, output, dist_tree=distance_huffman_tree)
                            huffman_code_length = 0
                            huffman_code = 0
                        elif decoded_value == 256:
                            break
                        else:
                            # 286 and 287 are included in the fixed Huffman code table, but they don't appear in the compressed data.
                            logger.error(f'Invalid Huffman code: {bin(huffman_code)}')
                            sys.exit(1)

                case 0b11:
                    logger.error('BTYPE 0b11 is reserved for future use')
                    sys.exit(1)
                case _:
                    assert False

            if bfinal:
                break

        return output.getvalue()

    def _decode_fixed_huffman_code(self, huffman_code: int, huffman_code_length: int) -> int | None:
        return self.FIXED_HUFFMAN_TREE.search(huffman_code, huffman_code_length)

    def _decode_LZ77(self, input_stream: BitStream, value: int, output_stream: io.BytesIO, dist_tree: tree.HuffmanTree | None = None) -> None:
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
        if dist_tree is None:
            dist_code = input_stream.read_bits(5)
        else:
            code = 0
            code_length = 0
            while True:
                code = (code << 1) | input_stream.read_bit()
                code_length += 1
                dist_code = dist_tree.search(code, code_length)
                if dist_code is not None:
                    break

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
        return self._decompress_zlib(data.getbuffer().tobytes())
