import zlib
import io

def decompress(data: io.BytesIO) -> bytes:
    decompressor = zlib.decompressobj()
    decompressed_data = decompressor.decompress(data.getbuffer())
    return decompressed_data
