import io
import sys

from loguru import logger

from .tree import HuffmanTree
from ..utils.bitstream import BitStream

class Deflate:
    def __init__(self, is_logging: bool = False) -> None:
        logger.remove()
        logger.add(sys.stdout, filter=lambda record: is_logging)
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not is_logging)

        self.FIXED_HUFFMAN_TREE = self.create_fixed_huffman_tree()
        self.CODE_LENGTH_CODE_TABLE_INDEXES = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]

    def decompress(self, data_stream: BitStream) -> bytes:
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

                    self._decompress_compressed_section(data_stream, output, self.FIXED_HUFFMAN_TREE, dist_tree=None)
                case 0b10:
                    # Compressed with dynamic Huffman codes

                    hlit = data_stream.read_bits(5, reverse=False)  # Number of literal/length codes - 257
                    hdist = data_stream.read_bits(5, reverse=False) # Number of distance codes - 1
                    hclen = data_stream.read_bits(4, reverse=False) # Number of code length codes - 4

                    code_length_code_tree = self._create_code_length_code_tree(data_stream, hclen)

                    literal_length_tree = self._create_literal_length_tree(data_stream, code_length_code_tree, hlit)
                    distance_tree = self._create_distance_tree(data_stream, code_length_code_tree, hdist)

                    self._decompress_compressed_section(data_stream, output, literal_length_tree, distance_tree)
                case 0b11:
                    logger.error('BTYPE 0b11 is reserved for future use')
                    sys.exit(1)
                case _:
                    assert False

            if bfinal:
                break

        return output.getvalue()

    @staticmethod
    def create_fixed_huffman_tree() -> HuffmanTree:
        huffman_tree = HuffmanTree()
        for value in range(0, 144):
            huffman_tree.insert(value, 0b00110000 + value, 8)
        for value in range(144, 256):
            huffman_tree.insert(value, 0b110010000 + value - 144, 9)
        for value in range(256, 280):
            huffman_tree.insert(value, 0b0000000 + value - 256, 7)
        for value in range(280, 288):
            huffman_tree.insert(value, 0b11000000 + value - 280, 8)
        return huffman_tree

    def _read_deflate_block_header(self, data: BitStream) -> tuple[bool, int]:
        bfinal = data.read_bit()
        btype = data.read_bits(2, reverse=False)
        return bfinal, btype

    def _create_code_length_code_tree(self, input_stream: BitStream, hclen: int) -> HuffmanTree:
        code_length_code_table = {}
        for i in range(hclen + 4):
            code_length_code_table[self.CODE_LENGTH_CODE_TABLE_INDEXES[i]] = input_stream.read_bits(3, reverse=False)
        for i in range(19):
            if i not in code_length_code_table:
                code_length_code_table[i] = 0
        return HuffmanTree.create_canonical_huffman_tree(code_length_code_table)

    def _create_tree_from_code_length_code_tree(self, input_stream: BitStream, code_length_code_tree: HuffmanTree, table_num: int) -> HuffmanTree:
        table = {}
        i = 0
        while i < table_num:
            huffman_code, huffman_code_length = 0, 0
            while True:
                huffman_code = (huffman_code << 1) | input_stream.read_bit()
                huffman_code_length += 1
                if huffman_code_length > code_length_code_tree.height:
                    logger.error(f'Invalid Huffman code length: equal to or greater than {huffman_code_length}')
                    sys.exit(1)

                decoded_value = code_length_code_tree.search(huffman_code, huffman_code_length)
                if decoded_value is None:
                    continue

                match decoded_value:
                    case 16:
                        # Repeat previous value 3-6 times
                        extra_bits = input_stream.read_bits(2, reverse=False)
                        for _ in range(3 + extra_bits):
                            table[i] = table[i - 1]
                            i += 1
                    case 17:
                        # Repeat 0 for 3-10 times
                        extra_bits = input_stream.read_bits(3, reverse=False)
                        for _ in range(3 + extra_bits):
                            table[i] = 0
                            i += 1
                    case 18:
                        # Repeat 0 for 11-138 times
                        extra_bits = input_stream.read_bits(7, reverse=False)
                        for _ in range(11 + extra_bits):
                            table[i] = 0
                            i += 1
                    case _:
                        table[i] = decoded_value
                        i += 1

                break

        return HuffmanTree.create_canonical_huffman_tree(table)

    def _create_literal_length_tree(self, input_stream: BitStream, code_length_code_tree: HuffmanTree, hlit: int) -> HuffmanTree:
        return self._create_tree_from_code_length_code_tree(input_stream, code_length_code_tree, hlit + 257)

    def _create_distance_tree(self, input_stream: BitStream, code_length_code_tree: HuffmanTree, hdist: int) -> HuffmanTree:
        return self._create_tree_from_code_length_code_tree(input_stream, code_length_code_tree, hdist + 1)

    def _decompress_compressed_section(
            self, input_stream: BitStream, output_stream: io.BytesIO, literal_length_tree: HuffmanTree, dist_tree: HuffmanTree | None = None
        ) -> None:
        huffman_code, huffman_code_length = 0, 0
        while True:
            huffman_code = (huffman_code << 1) | input_stream.read_bit()
            huffman_code_length += 1
            if huffman_code_length > literal_length_tree.height:
                logger.error(f'Invalid Huffman code length: equal to or greater than {huffman_code_length}')
                sys.exit(1)

            decoded_value = literal_length_tree.search(huffman_code, huffman_code_length)
            if decoded_value is None:
                continue

            if decoded_value in range(0, 256):
                output_stream.write(decoded_value.to_bytes(1))
                huffman_code_length = 0
                huffman_code = 0
            elif decoded_value == 256:
                break
            elif decoded_value in range(257, 286):
                self._decode_LZ77(input_stream, decoded_value, output_stream, dist_tree=dist_tree)
                huffman_code_length = 0
                huffman_code = 0
            else:
                # 286 and 287 are included in the fixed Huffman code table, but they don't appear in the compressed data.
                logger.error(f'Invalid Huffman code: {bin(huffman_code)}')
                sys.exit(1)

    def _decode_fixed_huffman_code(self, huffman_code: int, huffman_code_length: int) -> int | None:
        return self.FIXED_HUFFMAN_TREE.search(huffman_code, huffman_code_length)

    def _decode_LZ77(self, input_stream: BitStream, length_value: int, output_stream: io.BytesIO, dist_tree: HuffmanTree | None = None) -> None:
        # Get the length of the match
        if length_value in range(257, 265):
            base_match_length = 3 + length_value - 257
            extra_bits_length = 0
        elif length_value in range(265, 269):
            base_match_length = 11 + 2 * (length_value - 265)
            extra_bits_length = 1
        elif length_value in range(269, 273):
            base_match_length = 19 + 4 * (length_value - 269)
            extra_bits_length = 2
        elif length_value in range(273, 277):
            base_match_length = 35 + 8 * (length_value - 273)
            extra_bits_length = 3
        elif length_value in range(277, 281):
            base_match_length = 67 + 16 * (length_value - 277)
            extra_bits_length = 4
        elif length_value in range(281, 285):
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
            huffman_code, huffman_code_length = 0, 0
            while True:
                huffman_code = (huffman_code << 1) | input_stream.read_bit()
                huffman_code_length += 1
                if huffman_code_length > dist_tree.height:
                    logger.error(f'Invalid Huffman code length: equal to or greater than {huffman_code_length}')
                    sys.exit(1)

                dist_value = dist_tree.search(huffman_code, huffman_code_length)
                if dist_value is not None:
                    break

        # Get the distance of the match
        if dist_value in range(0, 4):
            base_match_distance = dist_value + 1
            extra_bits_length = 0
        elif dist_value in range(4, 6):
            base_match_distance = 5 + 2 * (dist_value - 4)
            extra_bits_length = 1
        elif dist_value in range(6, 8):
            base_match_distance = 9 + 4 * (dist_value - 6)
            extra_bits_length = 2
        elif dist_value in range(8, 10):
            base_match_distance = 17 + 8 * (dist_value - 8)
            extra_bits_length = 3
        elif dist_value in range(10, 12):
            base_match_distance = 33 + 16 * (dist_value - 10)
            extra_bits_length = 4
        elif dist_value in range(12, 14):
            base_match_distance = 65 + 32 * (dist_value - 12)
            extra_bits_length = 5
        elif dist_value in range(14, 16):
            base_match_distance = 129 + 64 * (dist_value - 14)
            extra_bits_length = 6
        elif dist_value in range(16, 18):
            base_match_distance = 257 + 128 * (dist_value - 16)
            extra_bits_length = 7
        elif dist_value in range(18, 20):
            base_match_distance = 513 + 256 * (dist_value - 18)
            extra_bits_length = 8
        elif dist_value in range(20, 22):
            base_match_distance = 1025 + 512 * (dist_value - 20)
            extra_bits_length = 9
        elif dist_value in range(22, 24):
            base_match_distance = 2049 + 1024 * (dist_value - 22)
            extra_bits_length = 10
        elif dist_value in range(24, 26):
            base_match_distance = 4097 + 2048 * (dist_value - 24)
            extra_bits_length = 11
        elif dist_value in range(26, 28):
            base_match_distance = 8193 + 4096 * (dist_value - 26)
            extra_bits_length = 12
        elif dist_value in range(28, 30):
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
