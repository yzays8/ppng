import io
import sys
from types import MappingProxyType

from loguru import logger

from .tree import HuffmanTree
from ..utils.bitstream import BitStream

# https://www.rfc-editor.org/rfc/rfc1951
class Deflate:
    def __init__(self, is_logging: bool = False) -> None:
        logger.remove()
        logger.add(sys.stdout, filter=lambda record: is_logging)
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not is_logging)

        self.FIXED_HUFFMAN_TREE = self._create_fixed_huffman_tree()
        self.CODE_LENGTH_CODE_TABLE_INDEXES = (16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15)
        self.MATCH_LENGTH_BASE_EXTRA_BITS_TABLE = self._get_match_lb_eb_table()
        self.MATCH_DISTANCE_BASE_EXTRA_BITS_TABLE = self._get_match_db_eb_table()

    def decompress(self, data_stream: BitStream) -> bytes:
        output = io.BytesIO()

        # Read deflate blocks.
        while True:
            bfinal, btype = self._read_deflate_block_header(data_stream)

            match btype:
                # No compression
                case 0b00:
                    len = data_stream.read_bytes(2, reverse=False, endian='little')
                    nlen = data_stream.read_bytes(2, reverse=False, endian='little')
                    if len != (~nlen & 0xFFFF):
                        logger.error('NLEN is not the one\'s complement of LEN')
                        sys.exit(1)
                    output.write(data_stream.read_bytes(len, reverse=False).to_bytes(len))

                # Compressed with fixed Huffman codes
                case 0b01:
                    self._decompress_compressed_section(data_stream, output, self.FIXED_HUFFMAN_TREE, distance_tree=None)

                # Compressed with dynamic Huffman codes
                case 0b10:
                    # https://www.rfc-editor.org/rfc/rfc1951#section-3.2.7
                    #
                    # In the dynamic Huffman code sequence, the following
                    #
                    # (1) 5 Bits: HLIT, # of Literal/Length codes - 257
                    # (2) 5 Bits: HDIST, # of Distance codes - 1
                    # (3) 4 Bits: HCLEN, # of Code Length codes - 4
                    # (4) A code length code lengths table
                    # (5) A literal/length code lengths table
                    # (6) A distance code lengths table
                    # (7) The actual compressed data
                    # (8) The end of the block
                    #
                    # are included in this order.
                    #
                    # The details of the tables (4), (5), (6):
                    #     (5) literal_length_table:
                    #           A table of Huffman code lengths used for the Huffman codes representing the repeated literals and their lengths
                    #     (6) distance_table:
                    #           A table of Huffman code lengths used for the Huffman codes representing the values of how far apart the same literal code occurs
                    #     (4) code_length_code_table:
                    #           A table of Huffman code lengths used for the Huffman codes representing the tables (5) and (6)

                    # (1), (2), (3)
                    hlit = data_stream.read_bits(5, reverse=False)
                    hdist = data_stream.read_bits(5, reverse=False)
                    hclen = data_stream.read_bits(4, reverse=False)

                    # (4), (5), (6)
                    code_length_code_tree = self._create_code_length_code_tree(data_stream, hclen)
                    literal_length_tree = self._create_tree_from_code_length_code_tree(data_stream, code_length_code_tree, hlit + 257)
                    distance_tree = self._create_tree_from_code_length_code_tree(data_stream, code_length_code_tree, hdist + 1)

                    # (7)
                    self._decompress_compressed_section(data_stream, output, literal_length_tree, distance_tree)

                case 0b11:
                    logger.error('BTYPE 0b11 is reserved for future use')
                    sys.exit(1)

                case _:
                    assert False

            if bfinal:
                break

        return output.getvalue()

    # https://www.rfc-editor.org/rfc/rfc1951#section-3.2.6
    @classmethod
    def _create_fixed_huffman_tree(cls) -> HuffmanTree:
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

    # https://www.rfc-editor.org/rfc/rfc1951#section-3.2.5
    @classmethod
    def _get_match_lb_eb_table(cls) -> MappingProxyType:
        """Returns the hash table of the match length base and extra bits"""
        table: dict[int, tuple[int, int]] = {}
        for length_value in range(257, 286):
            if 257 <= length_value < 265:
                table[length_value] = (3 + length_value - 257, 0)
            elif 265 <= length_value < 269:
                table[length_value] = (11 + 2 * (length_value - 265), 1)
            elif 269 <= length_value < 273:
                table[length_value] = (19 + 4 * (length_value - 269), 2)
            elif 273 <= length_value < 277:
                table[length_value] = (35 + 8 * (length_value - 273), 3)
            elif 277 <= length_value < 281:
                table[length_value] = (67 + 16 * (length_value - 277), 4)
            elif 281 <= length_value < 285:
                table[length_value] = (131 + 32 * (length_value - 281), 5)
            else:
                table[length_value] = (258, 0)
        return MappingProxyType(table)

    # https://www.rfc-editor.org/rfc/rfc1951#section-3.2.5
    @classmethod
    def _get_match_db_eb_table(cls) -> MappingProxyType:
        """Returns the hash table of the match distance base and extra bits"""
        table: dict[int, tuple[int, int]] = {}
        for dist_value in range(0, 30):
            if 0 <= dist_value < 4:
                table[dist_value] = (dist_value + 1, 0)
            elif 4 <= dist_value < 6:
                table[dist_value] = (5 + 2 * (dist_value - 4), 1)
            elif 6 <= dist_value < 8:
                table[dist_value] = (9 + 4 * (dist_value - 6), 2)
            elif 8 <= dist_value < 10:
                table[dist_value] = (17 + 8 * (dist_value - 8), 3)
            elif 10 <= dist_value < 12:
                table[dist_value] = (33 + 16 * (dist_value - 10), 4)
            elif 12 <= dist_value < 14:
                table[dist_value] = (65 + 32 * (dist_value - 12), 5)
            elif 14 <= dist_value < 16:
                table[dist_value] = (129 + 64 * (dist_value - 14), 6)
            elif 16 <= dist_value < 18:
                table[dist_value] = (257 + 128 * (dist_value - 16), 7)
            elif 18 <= dist_value < 20:
                table[dist_value] = (513 + 256 * (dist_value - 18), 8)
            elif 20 <= dist_value < 22:
                table[dist_value] = (1025 + 512 * (dist_value - 20), 9)
            elif 22 <= dist_value < 24:
                table[dist_value] = (2049 + 1024 * (dist_value - 22), 10)
            elif 24 <= dist_value < 26:
                table[dist_value] = (4097 + 2048 * (dist_value - 24), 11)
            elif 26 <= dist_value < 28:
                table[dist_value] = (8193 + 4096 * (dist_value - 26), 12)
            else:
                table[dist_value] = (16385 + 8192 * (dist_value - 28), 13)
        return MappingProxyType(table)

    # https://www.rfc-editor.org/rfc/rfc1951#section-3.2.3
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

    def _create_tree_from_code_length_code_tree(
            self, input_stream: BitStream, code_length_code_tree: HuffmanTree, table_num: int
        ) -> HuffmanTree:
        table: dict[int, int] = {}
        i = 0
        while i < table_num:
            huffman_code, huffman_code_length = 0, 0
            while True:
                huffman_code = (huffman_code << 1) | input_stream.read_bit()
                huffman_code_length += 1
                if huffman_code_length > code_length_code_tree.height:
                    logger.error(f'Invalid Huffman code length: equal to or greater than {huffman_code_length}')
                    sys.exit(1)

                decoded_value = code_length_code_tree.search_map(huffman_code, huffman_code_length)
                if decoded_value is None:
                    continue

                match decoded_value:
                    case 16:
                        # Repeat previous value 3-6 times.
                        extra_bits = input_stream.read_bits(2, reverse=False)
                        for _ in range(3 + extra_bits):
                            table[i] = table[i - 1]
                            i += 1
                    case 17:
                        # Repeat 0 for 3-10 times.
                        extra_bits = input_stream.read_bits(3, reverse=False)
                        for _ in range(3 + extra_bits):
                            table[i] = 0
                            i += 1
                    case 18:
                        # Repeat 0 for 11-138 times.
                        extra_bits = input_stream.read_bits(7, reverse=False)
                        for _ in range(11 + extra_bits):
                            table[i] = 0
                            i += 1
                    case _:
                        table[i] = decoded_value
                        i += 1

                break

        return HuffmanTree.create_canonical_huffman_tree(table)

    def _decompress_compressed_section(
            self,
            input_stream: BitStream,
            output_stream: io.BytesIO,
            literal_length_tree: HuffmanTree,
            distance_tree: HuffmanTree | None = None
        ) -> None:
        huffman_code, huffman_code_length = 0, 0
        while True:
            huffman_code = (huffman_code << 1) | input_stream.read_bit()
            huffman_code_length += 1
            if huffman_code_length > literal_length_tree.height:
                logger.error(f'Invalid Huffman code length: equal to or greater than {huffman_code_length}')
                sys.exit(1)

            decoded_value = literal_length_tree.search_map(huffman_code, huffman_code_length)
            if decoded_value is None:
                continue

            if 0 <= decoded_value < 256:
                output_stream.write(decoded_value.to_bytes(1))
                huffman_code_length = 0
                huffman_code = 0
            elif decoded_value == 256:
                break
            elif 257 <= decoded_value < 286:
                self._decode_LZ77(input_stream, decoded_value, output_stream, distance_tree=distance_tree)
                huffman_code_length = 0
                huffman_code = 0
            else:
                # 286 and 287 are included in the fixed Huffman code table, but they don't appear in the compressed data.
                logger.error(f'Invalid Huffman code: {bin(huffman_code)}')
                sys.exit(1)

    def _decode_LZ77(
            self, input_stream: BitStream, length_value: int, output_stream: io.BytesIO, distance_tree: HuffmanTree | None = None
        ) -> None:
        # Get the length of the repeated literal.
        base_match_length, extra_bits_length = self.MATCH_LENGTH_BASE_EXTRA_BITS_TABLE.get(length_value)
        if base_match_length is None:
            logger.error(f'Invalid length code: {length_value}')
            sys.exit(1)
        extra_bits = input_stream.read_bits(extra_bits_length, reverse=False)
        match_length = base_match_length + extra_bits

        # Get the value that represents the distance and the extra bits in the MATCH_DISTANCE_BASE_EXTRA_BITS_TABLE.
        if distance_tree is None:
            # Compressed with fixed Huffman codes
            dist_value = input_stream.read_bits(5)
        else:
            # Compressed with dynamic Huffman codes
            huffman_code, huffman_code_length = 0, 0
            while True:
                huffman_code = (huffman_code << 1) | input_stream.read_bit()
                huffman_code_length += 1
                if huffman_code_length > distance_tree.height:
                    logger.error(f'Invalid Huffman code length: equal to or greater than {huffman_code_length}')
                    sys.exit(1)

                dist_value = distance_tree.search_map(huffman_code, huffman_code_length)
                if dist_value is not None:
                    break

        # Get the distance of the same literal code occurs.
        base_match_distance, extra_bits_length = self.MATCH_DISTANCE_BASE_EXTRA_BITS_TABLE.get(dist_value)
        if base_match_distance is None:
            logger.error(f'Invalid distance code: {dist_value}')
            sys.exit(1)
        extra_bits = input_stream.read_bits(extra_bits_length, reverse=False)
        match_distance = base_match_distance + extra_bits

        # Copy the matched literal to the output stream.
        for _ in range(match_length):
            output_stream.write(output_stream.getvalue()[-match_distance].to_bytes(1))
