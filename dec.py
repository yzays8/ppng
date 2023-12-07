import sys
import io
from typing import Tuple

IMAGE_FILE = 'image/test.png'

def decode_png(f: io.BufferedReader) -> None:
    read_header(f)

    length, type, data, crc = read_chunk(f)
    if type == 'IHDR':
        if length != 13:
            print('Invalid IHDR chunk')
            sys.exit(1)
        width = int.from_bytes(data[0:4])
        height = int.from_bytes(data[4:8])
        bit_depth = data[8]
        color_type = data[9]
        compression_method = data[10]
        filter_method = data[11]
        interlace_method = data[12]
        print(f'Image size: {width}x{height}')
        print(f'Bit depth: {bit_depth}')
        print(f'Color type: {color_type}')
        print(f'Compression method: {compression_method}')
        print(f'Filter method: {filter_method}')
        print(f'Interlace method: {interlace_method}')
    else:
        print('Invalid IHDR chunk')
        sys.exit(1)

    IDAT_chunk_data = io.BytesIO()

    while True:
        length, type, data, crc = read_chunk(f)
        if type == 'IDAT':
            IDAT_chunk_data.write(data)
        elif type == 'IEND':
            print('End of file')
            break
        else:
            print(f'Chunk "{type}" is not supported')
            sys.exit(1)

    print(f'All IDAT data size: {IDAT_chunk_data.getbuffer().nbytes / 1024} KB')

def read_header(f: io.BufferedReader) -> None:
    if f.read(8) == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
        print('PNG image')
    else:
        print('Invalid PNG image')
        sys.exit(1)

def read_chunk(f: io.BufferedReader) -> Tuple[int, str, bytes, int]:
    # Big endian
    chunk_length = int.from_bytes(f.read(4))
    chunk_type = f.read(4).decode('utf-8')
    chunk_data = f.read(chunk_length)
    chunk_crc = f.read(4)

    return chunk_length, chunk_type, chunk_data, chunk_crc

def main() -> None:
    try:
        with open(IMAGE_FILE, 'rb') as f:
            decode_png(f)
    except FileNotFoundError:
        print(f'File not found: {IMAGE_FILE}')
        sys.exit(1)
    except PermissionError:
        print(f'Permission denied: {IMAGE_FILE}')
        sys.exit(1)
    except Exception as e:
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
