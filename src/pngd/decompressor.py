import io
import sys
import zlib

from loguru import logger

from .adler32 import calculate_adler32

class Decompressor():
    def __init__(self, is_logging: bool = False) -> None:
        logger.remove()
        logger.add(sys.stdout, filter=lambda record: is_logging)

        # If a message higher than ERROR is logged while _is_logging is False, log it to stderr regardless of the logging flag
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not is_logging)

    def _decompress_zlib(self, data: io.BytesIO) -> bytes:
        self._interpret_zlib_header(*self._read_zlib_header(data))
        decompressed_data = self._decompress_deflate(data)
        adler32_checksum = int.from_bytes(data.read(4))
        calculated_checksum = calculate_adler32(decompressed_data)
        if adler32_checksum != calculated_checksum:
            logger.error(f'Invalid Adler-32 checksum (expected: {hex(adler32_checksum)}, actual: {hex(calculated_checksum)})')
            sys.exit(1)
        return decompressed_data

    def _read_zlib_header(self, data: io.BytesIO) -> tuple[int, int]:
        # Big endian
        cmf = data.read(1)
        flg = data.read(1)
        return int.from_bytes(cmf), int.from_bytes(flg)

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

    def _decompress_deflate(self, data: io.BytesIO) -> bytes:
        output = io.BytesIO()
        while True:
            byte = int.from_bytes(data.read(1))
            bfinal = byte & 0b1
            btype = (byte >> 1) & 0b11
            match btype:
                case 0b00:
                    # No compression
                    len = int.from_bytes(data.read(2), byteorder='little')
                    nlen = int.from_bytes(data.read(2), byteorder='little')
                    if len != (~nlen & 0xFFFF):
                        logger.error('NLEN is not the one\'s complement of LEN')
                        sys.exit(1)
                    output.write(data.read(len))
                case 0b01:
                    # Compressed with fixed Huffman codes
                    pass
                case 0b10:
                    # Compressed with dynamic Huffman codes
                    pass
                case 0b11:
                    logger.error('BTYPE 0b11 is reserved for future use')
                    sys.exit(1)
                case _:
                    assert False
            if bfinal:
                break
        return output.getvalue()

    def decompress(self, data: io.BytesIO) -> bytes:
        decompressor = zlib.decompressobj()
        decompressed_data = decompressor.decompress(data.getbuffer())
        return decompressed_data
