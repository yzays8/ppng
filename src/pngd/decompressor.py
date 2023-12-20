import zlib
import io

def decompress(data: io.BytesIO) -> bytes:
    decompressor = zlib.decompressobj()
    decompressed_data = decompressor.decompress(data.getbuffer())
    print(f'Decompressed data size: {len(decompressed_data) / 1024} KB')
    return decompressed_data
