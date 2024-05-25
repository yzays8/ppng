import io
import sys

from loguru import logger

from .zlib import Zlib

class Decompressor():
    def __init__(self, is_logging: bool = False) -> None:
        self._is_logging = is_logging
        logger.remove()
        logger.add(sys.stdout, filter=lambda record: is_logging)
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not is_logging)

    def decompress(self, data: io.BytesIO) -> bytes:
        logger.info('The decompression has started')
        ret = Zlib(self._is_logging).decompress(data.getbuffer().tobytes())
        logger.info('The decompression has completed successfully')
        return ret
