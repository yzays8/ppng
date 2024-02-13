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

        self.FIXED_HUFFMAN_TREE = self._create_fixed_huffman_tree()
        self.CODE_LENGTH_CODE_TABLE_INDEXES = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]

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

    def _create_fixed_huffman_tree(self) -> tree.HuffmanTree:
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

    def _read_deflate_block_header(self, data: BitStream) -> tuple[bool, int]:
        bfinal = data.read_bit()
        btype = data.read_bits(2, reverse=False)
        return bfinal, btype

    def _create_code_length_code_tree(self, input_stream: BitStream, hclen: int) -> tree.HuffmanTree:
        code_length_code_table = {}
        for i in range(hclen + 4):
            code_length_code_table[self.CODE_LENGTH_CODE_TABLE_INDEXES[i]] = input_stream.read_bits(3, reverse=False)
        for i in range(19):
            if i not in code_length_code_table:
                code_length_code_table[i] = 0
        return tree.make_canonical_huffman_tree(code_length_code_table)

    def _create_tree_from_code_length_code(self, input_stream: BitStream, code_length_code_tree: tree.HuffmanTree, table_num: int) -> tree.HuffmanTree:
        table = {}
        i = 0
        while i < table_num:
            huffman_code, huffman_code_length = 0, 0
            while True:
                huffman_code = (huffman_code << 1) | input_stream.read_bit()
                huffman_code_length += 1
                decoded_value = code_length_code_tree.search(huffman_code, huffman_code_length)
                if decoded_value is None:
                    continue
                elif decoded_value == 16:
                    # Repeat previous value 3-6 times
                    extra_bits = input_stream.read_bits(2, reverse=False)
                    for _ in range(3 + extra_bits):
                        table[i] = table[i - 1]
                        i += 1
                elif decoded_value == 17:
                    # Repeat 0 for 3-10 times
                    extra_bits = input_stream.read_bits(3, reverse=False)
                    for _ in range(3 + extra_bits):
                        table[i] = 0
                        i += 1
                elif decoded_value == 18:
                    # Repeat 0 for 11-138 times
                    extra_bits = input_stream.read_bits(7, reverse=False)
                    for _ in range(11 + extra_bits):
                        table[i] = 0
                        i += 1
                else:
                    table[i] = decoded_value
                    i += 1
                break

        return tree.make_canonical_huffman_tree(table)

    def _create_literal_length_tree(self, input_stream: BitStream, code_length_code_tree: tree.HuffmanTree, hlit: int) -> tree.HuffmanTree:
        return self._create_tree_from_code_length_code(input_stream, code_length_code_tree, hlit + 257)

    def _create_distance_tree(self, input_stream: BitStream, code_length_code_tree: tree.HuffmanTree, hdist: int) -> tree.HuffmanTree:
        return self._create_tree_from_code_length_code(input_stream, code_length_code_tree, hdist + 1)

    def _decompress_deflate(self, data_stream: BitStream) -> bytes:
        output = io.BytesIO()

        # Read deflate blocks
        while True:
            bfinal, btype = self._read_deflate_block_header(data_stream)

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

                    self._read_compressed_data(data_stream, output, self.FIXED_HUFFMAN_TREE, dist_tree=None)
                case 0b10:
                    # Compressed with dynamic Huffman codes

                    hlit = data_stream.read_bits(5, reverse=False)  # Number of literal/length codes - 257
                    hdist = data_stream.read_bits(5, reverse=False) # Number of distance codes - 1
                    hclen = data_stream.read_bits(4, reverse=False) # Number of code length codes - 4

                    code_length_code_tree = self._create_code_length_code_tree(data_stream, hclen)

                    literal_length_tree = self._create_literal_length_tree(data_stream, code_length_code_tree, hlit)
                    distance_tree = self._create_distance_tree(data_stream, code_length_code_tree, hdist)

                    self._read_compressed_data(data_stream, output, literal_length_tree, distance_tree)
                case 0b11:
                    logger.error('BTYPE 0b11 is reserved for future use')
                    sys.exit(1)
                case _:
                    assert False

            if bfinal:
                break

        return output.getvalue()

    def _read_compressed_data(
            self, input_stream: BitStream, output_stream: io.BytesIO, literal_length_tree: tree.HuffmanTree, dist_tree: tree.HuffmanTree | None = None
        ) -> None:
        huffman_code, huffman_code_length = 0, 0
        while True:
            huffman_code = (huffman_code << 1) | input_stream.read_bit()
            huffman_code_length += 1

            decoded_value = literal_length_tree.search(huffman_code, huffman_code_length)
            if decoded_value is None:
                continue
            elif decoded_value in range(0, 255 + 1):
                output_stream.write(decoded_value.to_bytes(1))
                huffman_code_length = 0
                huffman_code = 0
            elif decoded_value in range(257, 285 + 1):
                self._decode_LZ77(input_stream, decoded_value, output_stream, dist_tree=dist_tree)
                huffman_code_length = 0
                huffman_code = 0
            elif decoded_value == 256:
                break
            else:
                # 286 and 287 are included in the fixed Huffman code table, but they don't appear in the compressed data.
                logger.error(f'Invalid Huffman code: {bin(huffman_code)}')
                sys.exit(1)

    def _decode_fixed_huffman_code(self, huffman_code: int, huffman_code_length: int) -> int | None:
        return self.FIXED_HUFFMAN_TREE.search(huffman_code, huffman_code_length)

    def _decode_LZ77(self, input_stream: BitStream, length_value: int, output_stream: io.BytesIO, dist_tree: tree.HuffmanTree | None = None) -> None:
        # Get the length of the match
        if length_value in range(257, 264 + 1):
            base_match_length = 3 + length_value - 257
            extra_bits_length = 0
        elif length_value in range(265, 268 + 1):
            base_match_length = 11 + 2 * (length_value - 265)
            extra_bits_length = 1
        elif length_value in range(269, 272 + 1):
            base_match_length = 19 + 4 * (length_value - 269)
            extra_bits_length = 2
        elif length_value in range(273, 276 + 1):
            base_match_length = 35 + 8 * (length_value - 273)
            extra_bits_length = 3
        elif length_value in range(277, 280 + 1):
            base_match_length = 67 + 16 * (length_value - 277)
            extra_bits_length = 4
        elif length_value in range(281, 284 + 1):
            base_match_length = 131 + 32 * (length_value - 281)
            extra_bits_length = 5
        elif length_value == 285:
            base_match_length = 258
            extra_bits_length = 0
        else:
            logger.error(f'Invalid decoded value: {length_value}')
            sys.exit(1)
        extra_bits = input_stream.read_bits(extra_bits_length, reverse=False)
        match_length = base_match_length + extra_bits

        # Get the distance of the match
        if dist_tree is None:
            # Compressed with fixed Huffman codes
            dist_value = input_stream.read_bits(5)
        else:
            # Compressed with dynamic Huffman codes
            huffman_code = 0
            huffman_code_length = 0
            while True:
                huffman_code = (huffman_code << 1) | input_stream.read_bit()
                huffman_code_length += 1
                dist_value = dist_tree.search(huffman_code, huffman_code_length)
                if dist_value is not None:
                    break

        # Get the distance of the match
        if dist_value in range(0, 3 + 1):
            base_match_distance = dist_value + 1
            extra_bits_length = 0
        elif dist_value in range(4, 5 + 1):
            base_match_distance = 5 + 2 * (dist_value - 4)
            extra_bits_length = 1
        elif dist_value in range(6, 7 + 1):
            base_match_distance = 9 + 4 * (dist_value - 6)
            extra_bits_length = 2
        elif dist_value in range(8, 9 + 1):
            base_match_distance = 17 + 8 * (dist_value - 8)
            extra_bits_length = 3
        elif dist_value in range(10, 11 + 1):
            base_match_distance = 33 + 16 * (dist_value - 10)
            extra_bits_length = 4
        elif dist_value in range(12, 13 + 1):
            base_match_distance = 65 + 32 * (dist_value - 12)
            extra_bits_length = 5
        elif dist_value in range(14, 15 + 1):
            base_match_distance = 129 + 64 * (dist_value - 14)
            extra_bits_length = 6
        elif dist_value in range(16, 17 + 1):
            base_match_distance = 257 + 128 * (dist_value - 16)
            extra_bits_length = 7
        elif dist_value in range(18, 19 + 1):
            base_match_distance = 513 + 256 * (dist_value - 18)
            extra_bits_length = 8
        elif dist_value in range(20, 21 + 1):
            base_match_distance = 1025 + 512 * (dist_value - 20)
            extra_bits_length = 9
        elif dist_value in range(22, 23 + 1):
            base_match_distance = 2049 + 1024 * (dist_value - 22)
            extra_bits_length = 10
        elif dist_value in range(24, 25 + 1):
            base_match_distance = 4097 + 2048 * (dist_value - 24)
            extra_bits_length = 11
        elif dist_value in range(26, 27 + 1):
            base_match_distance = 8193 + 4096 * (dist_value - 26)
            extra_bits_length = 12
        elif dist_value in range(28, 29 + 1):
            base_match_distance = 16385 + 8192 * (dist_value - 28)
            extra_bits_length = 13
        else:
            logger.error(f'Invalid distance code: {dist_value}')
            sys.exit(1)
        extra_bits = input_stream.read_bits(extra_bits_length, reverse=False)
        match_distance = base_match_distance + extra_bits

        # Copy the match to the output
        for _ in range(match_length):
            output_stream.write(output_stream.getvalue()[-match_distance].to_bytes(1))

    def decompress(self, data: io.BytesIO) -> bytes:
        return self._decompress_zlib(data.getbuffer().tobytes())
