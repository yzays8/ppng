import sys
import io
import numpy as np

from toolz import pipe
from loguru import logger

from . import crc32
from . import decompressor

class Decoder:
    def __init__(self, is_logging: bool = False):
        self._is_logging = is_logging

        logger.remove()
        logger.add(sys.stdout, filter=lambda record: self._is_logging)

        # If a message higher than ERROR is logged while _is_logging is False, log it to stderr regardless of the logging flag
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not self._is_logging)

    def decode_png(self, f: io.BufferedReader) -> np.ndarray:
        if not self._validate_header(f):
            logger.error('Invalid PNG image')
            sys.exit(1)

        width, height, bit_depth, color_type, compression_method, filter_method, interlace_method \
            = self._read_IHDR(f)

        IDAT_chunk_data = io.BytesIO()

        gamma: float = None

        while True:
            length, type, data, crc = self._read_chunk(f)
            if not crc32.check_crc32(type, data, crc):
                sys.exit(1)

            match type:
                case 'IDAT':
                    IDAT_chunk_data.write(data)
                case 'IEND':
                    break
                case 'tEXt':
                    keyword, text = data.split(b'\x00', 1)
                    if len(text) > 0:
                        logger.info(f'tEXt: {keyword.decode("utf-8")} {text.decode("latin-1")}')
                    else:
                        logger.info(f'tEXt: {keyword.decode("utf-8")}')
                case 'tIME':
                    if length != 7:
                        logger.error('Invalid tIME chunk')
                        sys.exit(1)
                    year, month, day, hour, minute, second \
                        = int.from_bytes(data[:2]), data[2], data[3], data[4], data[5], data[6]
                    logger.info(f'tIME: {year}-{month}-{day} {hour:02d}:{minute:02d}:{second:02d}')
                case 'gAMA':
                    if length != 4:
                        logger.error('Invalid gAMA chunk')
                        sys.exit(1)
                    # The data is a 4-byte unsigned integer, representing gamma times 100000 and rounded to the nearest integer.
                    gamma = int.from_bytes(data) / 100000
                    logger.info(f'gAMA: {gamma}')
                case _:
                    logger.warning(f'Chunk "{type}" is not supported')
                    # sys.exit(1)

        logger.info(f'All IDAT data size: {IDAT_chunk_data.getbuffer().nbytes / 1024} KB')

        bytes_per_pixel = self._get_bytes_per_pixel(color_type, bit_depth)
        logger.info(f'Bytes per pixel: {bytes_per_pixel}')

        return pipe(
            IDAT_chunk_data,
            decompressor.decompress,
            lambda x: self._restore_filtered_image(x, width, height, bytes_per_pixel),
            lambda x: self._adjust_color_data(x, height, width, color_type, bit_depth),
            lambda x: self._gamma_correct(x, color_type, bit_depth, gamma) if gamma else x
        )

    def _gamma_correct(self, color_data: np.ndarray,  color_type: int, bit_depth: int, gamma: float) -> np.ndarray:
        # If gamma is 0.45455, gamma corrected value is same as original value
        if gamma != 0.45455:
            lut_exp = 1.0
            crt_exp = 2.2
            decoding_exp = 1 / (gamma * lut_exp * crt_exp)

            # Create gamma table
            if bit_depth == 8:
                gamma_table = np.array([int(pow(i / 255, decoding_exp) * 255) for i in range(256)])
            elif bit_depth == 16:
                gamma_table = np.array([int(pow(i / 65535, decoding_exp) * 65535) for i in range(65536)])
            else:
                logger.error(f'{bit_depth} bit is not allowed for gamma correction')
                sys.exit(1)

            if color_type == 2 or color_type == 6:
                if bit_depth == 8 or bit_depth == 16:
                    # Alpha channel is not gamma corrected
                    color_data[:, :, 0] = gamma_table[color_data[:, :, 0]]
                    color_data[:, :, 1] = gamma_table[color_data[:, :, 1]]
                    color_data[:, :, 2] = gamma_table[color_data[:, :, 2]]
                else:
                    assert False, f'{bit_depth} bit for color type {color_type} is not allowed'
            elif color_type == 3:
                logger.error(f'Not implemented color type {color_type}')
                sys.exit(1)
            elif color_type == 0 or color_type == 4:
                logger.error(f'{color_type} is not allowed for gamma correction')
                sys.exit(1)
            else:
                assert False

        return color_data

    def _adjust_color_data(self, color_data: np.ndarray, height: int, width: int, color_type: int, bit_depth: int) -> np.ndarray:
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
                logger.error(f'{bit_depth} bit for color type {color_type} is not implemented')
                sys.exit(1)
            else:
                logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
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
                logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
                sys.exit(1)
        elif color_type == 3:
            # palette index
            logger.error(f'Not implemented {color_type}')
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
                        gray: np.uint16 = color_data[i][j * 4] << 8 |  color_data[i][j * 4 + 1]
                        alpha: np.uint16 = color_data[i][j * 4 + 2] << 8 |  color_data[i][j * 4 + 3]
                        new_color_data[i][j][0] = new_color_data[i][j][1] = new_color_data[i][j][2] = new_color_data[i][j][3] = gray
                        new_color_data[i][j][3] = alpha
            else:
                logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
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
                logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
                sys.exit(1)
        else:
            logger.error(f'Color type {color_type} is not allowed')
            sys.exit(1)

        assert new_color_data is not None, 'new_color_data is None'

        return new_color_data

    def _restore_filtered_image(self, decompressed_data: bytes, width: int, height: int, bytes_per_pixel: int) -> np.ndarray:
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
                logger.error(f'Unsupported filter type: {filter_type}')
                sys.exit(1)

        return color_data

    def _get_bytes_per_pixel(self, color_type: int, bit_depth: int) -> int:
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

    def _validate_header(self, f: io.BufferedReader) -> bool:
        if f.read(8) != b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
            return False
        return True

    def _read_chunk(self, f: io.BufferedReader) -> tuple[int, str, bytes, int]:
        # Big endian
        chunk_length = int.from_bytes(f.read(4))
        chunk_type = f.read(4).decode('utf-8')
        chunk_data = f.read(chunk_length)
        chunk_crc = int.from_bytes(f.read(4))

        return chunk_length, chunk_type, chunk_data, chunk_crc

    def _read_IHDR(self, f: io.BufferedReader) -> tuple[int, int, int, int, int, int, int]:
        length, type, data, crc = self._read_chunk(f)
        if not crc32.check_crc32(type, data, crc):
            sys.exit(1)

        if type == 'IHDR':
            if length != 13:
                logger.error('Invalid IHDR chunk')
                sys.exit(1)
            width, height = map(int.from_bytes, (data[0:4], data[4:8]))
            bit_depth, color_type, compression_method, filter_method, interlace_method \
                = data[8], data[9], data[10], data[11], data[12]

            logger.info(f'Image size: {width}x{height}')
            logger.info(f'Bit depth: {bit_depth}')
            logger.info(f'Color type: {color_type}')
            logger.info(f'Compression method: {compression_method}')
            logger.info(f'Filter method: {filter_method}')
            logger.info(f'Interlace method: {interlace_method}')
        else:
            logger.error(f'Invalid IHDR chunk')
            sys.exit(1)

        return width, height, bit_depth, color_type, compression_method, filter_method, interlace_method
