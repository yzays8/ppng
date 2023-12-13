import sys
import io
import zlib
import numpy as np
import cv2
from typing import Tuple

def decode_png(f: io.BufferedReader) -> None:
    if not validate_header(f):
        sys.exit(1)

    width, height, bit_depth, color_type, compression_method, filter_method, interlace_method\
        = read_IHDR(f)

    IDAT_chunk_data = io.BytesIO()

    while True:
        length, type, data, crc = read_chunk(f)
        if type == 'IDAT':
            IDAT_chunk_data.write(data)
        elif type == 'IEND':
            break
        elif type == 'tEXt':
            keyword, text = data.split(b'\x00', 1)
            print(f'tEXt Keyword: {keyword.decode("utf-8")}')
            if len(text) > 0:
                print(f'\ttEXt Text: {text.decode("latin-1")}')
        elif type == 'tIME':
            if length != 7:
                print('Invalid tIME chunk')
                sys.exit(1)
            year, month, day, hour, minute, second\
                = int.from_bytes(data[:2]), data[2], data[3], data[4], data[5], data[6]
            print(f'tIME: {year}-{month}-{day} {hour:02d}:{minute:02d}:{second:02d}')
        else:
            print(f'Chunk "{type}" is not supported')
            # sys.exit(1)

    print(f'All IDAT data size: {IDAT_chunk_data.getbuffer().nbytes / 1024} KB')

    decompressed_data = decompress(IDAT_chunk_data)

    bytes_per_pixel = get_bytes_per_pixel(color_type, bit_depth)
    print(f'Bytes per pixel: {bytes_per_pixel}')

    color_data = restore_filtered_image(decompressed_data, width, height, bytes_per_pixel)
    adjusted_image_data = adjust_color_data(color_data, height, width, color_type, bit_depth)
    show_image(adjusted_image_data)

def adjust_color_data(color_data: np.ndarray, height: int, width: int, color_type: int, bit_depth: int) -> np.ndarray:
    new_color_data: np.ndarray = None

    if color_type == 0:
        # grayscale
        if bit_depth == 8:
            new_color_data = color_data.reshape(height, width)
        elif bit_depth == 16:
            new_color_data = np.ndarray(shape=(height, width), dtype=np.uint16)
            for i in range(height):
                for j in range(width):
                    new_color_data[i][j] = color_data[i][j * 2] << 8 |  color_data[i][j * 2 + 1]
        elif bit_depth == 1 or bit_depth == 2 or bit_depth == 4:
            print(f'{bit_depth} bit for color type {color_type} is not implemented')
            sys.exit(1)
        else:
            print(f'{bit_depth} bit for color type {color_type} is not allowed')
            sys.exit(1)
    elif color_type == 2:
        # RGB
        if bit_depth == 8:
            new_color_data = color_data.reshape(height, width, 3)
        elif bit_depth == 16:
            new_color_data = np.ndarray(shape=(height, width, 3), dtype=np.uint16)
            for i in range(height):
                for j in range(width):
                    new_color_data[i][j][0] = color_data[i][j * 6] << 8 |  color_data[i][j * 6 + 1]
                    new_color_data[i][j][1] = color_data[i][j * 6 + 2] << 8 |  color_data[i][j * 6 + 3]
                    new_color_data[i][j][2] = color_data[i][j * 6 + 4] << 8 |  color_data[i][j * 6 + 5]
        else:
            print(f'{bit_depth} bit for color type {color_type} is not allowed')
            sys.exit(1)
    elif color_type == 3:
        # palette index
        print(f'Not implemented {color_type}')
        sys.exit(1)
    elif color_type == 4:
        # grayscale + alpha
        if bit_depth == 8:
            color_data = color_data.reshape(height, width, 2)
            r = g = b = color_data[:, :, 0] # grayscale
            a = color_data[:, :, 1]         # alpha
            new_color_data = np.dstack((r, g, b, a))
        elif bit_depth == 16:
            new_color_data = np.ndarray(shape=(height, width, 4), dtype=np.uint16)
            for i in range(height):
                for j in range(width):
                    gray : np.uint16 = color_data[i][j * 4] << 8 |  color_data[i][j * 4 + 1]
                    alpha : np.uint16 = color_data[i][j * 4 + 2] << 8 |  color_data[i][j * 4 + 3]
                    new_color_data[i][j][0] = new_color_data[i][j][1] = new_color_data[i][j][2] = new_color_data[i][j][3] = gray
                    new_color_data[i][j][3] = alpha
        else:
            print(f'{bit_depth} bit for color type {color_type} is not allowed')
            sys.exit(1)
    elif color_type == 6:
        # RGB + alpha
        if bit_depth == 8:
            new_color_data = color_data.reshape(height, width, 4)
        elif bit_depth == 16:
            new_color_data = np.ndarray(shape=(height, width, 4), dtype=np.uint16)
            for i in range(height):
                for j in range(width):
                    new_color_data[i][j][0] = color_data[i][j * 8] << 8 |  color_data[i][j * 8 + 1]
                    new_color_data[i][j][1] = color_data[i][j * 8 + 2] << 8 |  color_data[i][j * 8 + 3]
                    new_color_data[i][j][2] = color_data[i][j * 8 + 4] << 8 |  color_data[i][j * 8 + 5]
                    new_color_data[i][j][3] = color_data[i][j * 8 + 6] << 8 |  color_data[i][j * 8 + 7]
        else:
            print(f'{bit_depth} bit for color type {color_type} is not allowed')
            sys.exit(1)
    else:
        print(f'Color type {color_type} is not allowed')
        sys.exit(1)

    assert new_color_data is not None, 'new_color_data is None'

    return new_color_data

def restore_filtered_image(decompressed_data: bytes, width: int, height: int, bytes_per_pixel: int) -> np.ndarray:
    color_data = np.ndarray(shape=(height, bytes_per_pixel * width), dtype=np.uint8)

    for i in range(height):
        bytes_per_line = 1 + width * bytes_per_pixel
        line_start_index = i * bytes_per_line
        filter_type = decompressed_data[line_start_index]
        data_start_index = line_start_index + 1

        if filter_type == 0:    # No filter
            for j in range(width * bytes_per_pixel):
                color_data[i][j] = decompressed_data[data_start_index + j]
        elif filter_type == 1:  # Sub filter
            for j in range(width * bytes_per_pixel):
                if j < bytes_per_pixel:
                    pre = 0
                else:
                    pre = color_data[i][j - bytes_per_pixel]

                color_data[i][j] = (decompressed_data[data_start_index + j] + pre) % 256
        elif filter_type == 2:  # Up filter
            for j in range(width * bytes_per_pixel):
                if i <= 0:
                    pre = 0
                else:
                    pre = color_data[i - 1][j]

                color_data[i][j] = (decompressed_data[data_start_index + j] + pre) % 256
        elif filter_type == 3:  # Average filter
            for j in range(width * bytes_per_pixel):
                pre = 0
                if j >= bytes_per_pixel and i > 0:
                    pre = int((color_data[i][j - bytes_per_pixel]) + int(color_data[i - 1][j])) // 2
                elif j >= bytes_per_pixel:
                    pre = color_data[i][j - bytes_per_pixel] // 2
                elif i > 0:
                    pre = color_data[i - 1][j] // 2

                color_data[i][j] = (decompressed_data[data_start_index + j] + pre) % 256
        elif filter_type == 4: # Paeth filter
            for j in range(width * bytes_per_pixel):
                a = int(color_data[i][j - bytes_per_pixel]) if j >= bytes_per_pixel else 0                  # left
                b = int(color_data[i - 1][j]) if i > 0 else 0                                               # upper
                c = int(color_data[i - 1][j - bytes_per_pixel]) if i > 0 and j >= bytes_per_pixel else 0    # upper left

                # Find the value closest to the prediction from among a, b, c
                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                if pa <= pb and pa <= pc:
                    pr = a
                elif pb <= pc:
                    pr = b
                else:
                    pr = c

                color_data[i][j] = (decompressed_data[data_start_index + j] + pr) % 256
        else:
            print(f'Unsupported filter type: {filter_type}')
            sys.exit(1)

    return color_data

def decompress(data: io.BytesIO) -> bytes:
    decompressor = zlib.decompressobj()
    decompressed_data = decompressor.decompress(data.getbuffer())
    print(f'Decompressed data size: {len(decompressed_data) / 1024} KB')
    return decompressed_data

def show_image(color_data: np.ndarray) -> None:
    # cv2 allows only BGR format
    new_color_data = cv2.cvtColor(color_data, cv2.COLOR_RGB2BGR)

    cv2.imshow('image', new_color_data)
    while True:
        # Wait for 100ms
        key = cv2.waitKey(100)

        # Quit if 'q' or ESC is pressed
        if key == ord('q') or key == 27:
            cv2.destroyAllWindows()
            break
        # Quit if the window is closed
        if cv2.getWindowProperty('image', cv2.WND_PROP_VISIBLE) < 1:
            break

    cv2.destroyAllWindows()

def get_bytes_per_pixel(color_type: int, bit_depth: int) -> int:
    if color_type == 0:
        # grayscale
        bits_per_pixel = bit_depth
    if color_type == 2:
        # RGB
        bits_per_pixel = bit_depth * 3
    if color_type == 3:
        # palette index
        bits_per_pixel = bit_depth
    if color_type == 4:
        # grayscale + alpha
        bits_per_pixel = bit_depth * 2
    if color_type == 6:
        # RGB + alpha
        bits_per_pixel = bit_depth * 4

    return int(bits_per_pixel / 8)

def validate_header(f: io.BufferedReader) -> bool:
    if f.read(8) != b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
        print('Invalid PNG image')
        return False
    return True

def read_chunk(f: io.BufferedReader) -> Tuple[int, str, bytes, int]:
    # Big endian
    chunk_length = int.from_bytes(f.read(4))
    chunk_type = f.read(4).decode('utf-8')
    chunk_data = f.read(chunk_length)
    chunk_crc = f.read(4)

    return chunk_length, chunk_type, chunk_data, chunk_crc

def read_IHDR(f: io.BufferedReader) -> Tuple[int, int, int, int, int, int, int]:
    length, type, data, crc = read_chunk(f)
    if type == 'IHDR':
        if length != 13:
            print('Invalid IHDR chunk')
            sys.exit(1)
        width, height = map(int.from_bytes, (data[0:4], data[4:8]))
        bit_depth, color_type, compression_method, filter_method, interlace_method\
            = data[8], data[9], data[10], data[11], data[12]
        print(f'Image size: {width}x{height}')
        print(f'Bit depth: {bit_depth}')
        print(f'Color type: {color_type}')
        print(f'Compression method: {compression_method}')
        print(f'Filter method: {filter_method}')
        print(f'Interlace method: {interlace_method}')
    else:
        print('Invalid IHDR chunk')
        sys.exit(1)

    return width, height, bit_depth, color_type, compression_method, filter_method, interlace_method
