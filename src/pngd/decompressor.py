import io
import sys
import zlib

from loguru import logger

class Decompressor():
    def __init__(self, is_logging: bool = False) -> None:
        logger.remove()
        logger.add(sys.stdout, filter=lambda record: is_logging)

        # If a message higher than ERROR is logged while _is_logging is False, log it to stderr regardless of the logging flag
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not is_logging)

    def decompress(self, data: io.BytesIO) -> bytes:
        decompressor = zlib.decompressobj()
        decompressed_data = decompressor.decompress(data.getbuffer())
        return decompressed_data
