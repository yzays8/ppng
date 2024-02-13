import io

from .zlib import Zlib

class Decompressor():
    def __init__(self, is_logging: bool = False) -> None:
        self.is_logging = is_logging

    def decompress(self, data: io.BytesIO) -> bytes:
        return Zlib(self.is_logging).decompress_zlib(data.getbuffer().tobytes())