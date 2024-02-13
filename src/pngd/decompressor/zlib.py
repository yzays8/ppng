import sys

from loguru import logger

from .adler32 import calculate_adler32
from .deflate import Deflate
from ..utils.bitstream import BitStream

class Zlib:
    def __init__(self, is_logging: bool = False) -> None:
        self.is_logging = is_logging

        logger.remove()
        logger.add(sys.stdout, filter=lambda record: is_logging)
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not is_logging)

    def decompress_zlib(self, data: bytes) -> bytes:
        bit_stream = BitStream(data)

        self._interpret_zlib_header(*self._read_zlib_header(bit_stream))

        decompressed_data = Deflate(self.is_logging).decompress_deflate(bit_stream)

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

    def _interpret_zlib_header(self, cmf: int, flg: int) -> None:
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
