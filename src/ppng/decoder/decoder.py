import sys
import io

import numpy as np
from toolz import pipe
from loguru import logger

from .. import decompressor
from . import crc32

class Decoder:
    def __init__(self, is_logging: bool = False):
        self._is_logging = is_logging

        logger.remove()
        logger.add(sys.stdout, filter=lambda record: self._is_logging)

        # If a message higher than ERROR is logged while _is_logging is False, log it to stderr regardless of the logging flag
        logger.add(sys.stderr, level='ERROR', filter=lambda record: not self._is_logging)

    def decode_png(self, f: io.BufferedReader) -> np.ndarray:
        if not self._is_valid_header(f):
            logger.error('Invalid PNG image')
            sys.exit(1)

        width, height, bit_depth, color_type, compression_method, filter_method, interlace_method \
            = self._read_IHDR(f)

        if compression_method != 0:
            logger.error(f'Compression method {compression_method} is not implemented')
            sys.exit(1)

        IDAT_chunk_data = io.BytesIO()

        gamma: float = None
        palette: np.ndarray = None

        while True:
            length, type, data, crc = self._read_chunk(f)

            # CRC32 checksum for PNG chunks is calculated from the chunk type and chunk data.
            calculated_crc32_checksum = crc32.calculate_crc32(type.encode('utf-8') + data)
            if calculated_crc32_checksum != crc:
                logger.error(f'Invalid CRC for chunk "{type}" (expected: {hex(crc)}, actual: {hex(calculated_crc32_checksum)})')
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
                case 'zTXt':
                    keyword, others = data.split(b'\x00', 1)
                    compression_method, compressed_text = others[0], others[1:]
                    if compression_method != 0:
                        logger.error('Invalid zTXt chunk')
                        sys.exit(1)
                    text = decompressor.Decompressor(self._is_logging).decompress(io.BytesIO(compressed_text))
                    if len(text) > 0:
                        logger.info(f'zTXt: {keyword.decode("utf-8")} {text.decode("latin-1")}')
                    else:
                        logger.info(f'zTXt: {keyword.decode("utf-8")}')
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
                case 'PLTE':
                    # The data in PLTE chunk is a set of RGB values (entry), each 3 bytes long.
                    # The number of palette entries is up to 256.
                    if (length % 3 != 0) or (length > (1 << 8) * 3) or (length < 3):
                        logger.error('Invalid PLTE chunk')
                        sys.exit(1)
                    entry_num = length // 3
                    logger.info(f'PLTE: {entry_num} entries')
                    # The order of data in each entry is R, G, B.
                    palette = np.frombuffer(data, dtype=np.uint8).reshape(entry_num, 3)
                case _:
                    logger.warning(f'Chunk "{type}" is not supported')

        logger.info(f'All IDAT data size: {IDAT_chunk_data.getbuffer().nbytes / 1024} KB')

        bytes_per_pixel = self._get_bytes_per_pixel(color_type, bit_depth)
        logger.info(f'Bytes per pixel: {bytes_per_pixel}')

        return pipe(
            IDAT_chunk_data,
            decompressor.Decompressor(self._is_logging).decompress,
            lambda x: self._remove_filter(x, width, height, bytes_per_pixel, bit_depth),
            lambda x: self._generate_color_data(x, height, width, color_type, bit_depth, palette),
            lambda x: self._gamma_correct(x, color_type, bit_depth, gamma) if gamma else x
        )

    def _gamma_correct(self, color_data: np.ndarray,  color_type: int, bit_depth: int, gamma: float) -> np.ndarray:
        # If gamma is 0.45455, gamma corrected value is same as original value
        if gamma == 0.45455:
            return color_data

        logger.info('Start gamma correction')

        lut_exp = 1.0
        crt_exp = 2.2
        decoding_exp = 1 / (gamma * lut_exp * crt_exp)

        # Create gamma table
        match bit_depth:
            case 8:
                gamma_table = np.array([int(pow(i / 255, decoding_exp) * 255) for i in range(256)])
            case 16:
                gamma_table = np.array([int(pow(i / 65535, decoding_exp) * 65535) for i in range(65536)])
            case _:
                logger.error(f'{bit_depth} bit is not allowed for gamma correction')
                sys.exit(1)

        match color_type:
            case 2 | 3 | 6:
                if bit_depth == 8 or bit_depth == 16:
                    # Alpha channel is not gamma corrected
                    color_data[:, :, 0] = gamma_table[color_data[:, :, 0]]
                    color_data[:, :, 1] = gamma_table[color_data[:, :, 1]]
                    color_data[:, :, 2] = gamma_table[color_data[:, :, 2]]
                else:
                    logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
                    sys.exit(1)
            case 0 | 4:
                logger.error(f'{color_type} is not allowed for gamma correction')
                sys.exit(1)
            case _:
                logger.error(f'Color type {color_type} is not allowed')
                sys.exit(1)

        logger.info('Finish gamma correction successfully')
        return color_data

    def _generate_color_data(self, data: np.ndarray, height: int, width: int, color_type: int, bit_depth: int, palette: np.ndarray = None) -> np.ndarray:
        logger.info('Start generating color data')

        match color_type:
            case 0:
                # grayscale
                match bit_depth:
                    case 1:
                        new_data = np.ndarray(shape=(height, width), dtype=np.uint8)
                        for i in range(height):
                            for j in range(width):
                                new_data[i][j] = (data[i][j // 8] >> (7 - j % 8) & 0b1) * 0xFF
                    case 2:
                        new_data = np.ndarray(shape=(height, width), dtype=np.uint8)
                        for i in range(height):
                            for j in range(width):
                                # Map 0b00 ~ 0b11 to 0x00 ~ 0xFF
                                new_data[i][j] = (data[i][j // 4] >> (6 - 2 * (j % 4)) & 0b11) * 0x55
                    case 4:
                        new_data = np.ndarray(shape=(height, width), dtype=np.uint8)
                        for i in range(height):
                            for j in range(width):
                                # Map 0b0000 ~ 0b1111 to 0x00 ~ 0xFF
                                new_data[i][j] = (data[i][j // 2] >> (4 - 4 * (j % 2)) & 0b1111) * 0x11
                    case 8:
                        new_data = data.reshape(height, width)
                    case 16:
                        new_data = np.ndarray(shape=(height, width), dtype=np.uint16)
                        for i in range(height):
                            for j in range(width):
                                new_data[i][j] = data[i][j * 2] << 8 |  data[i][j * 2 + 1]
                    case _:
                        logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
                        sys.exit(1)
            case 2:
                # RGB
                if palette is not None:
                    logger.warning('Palette is found but color type is 2')
                match bit_depth:
                    case 8:
                        new_data = data.reshape(height, width, 3)
                    case 16:
                        new_data = np.ndarray(shape=(height, width, 3), dtype=np.uint16)
                        for i in range(height):
                            for j in range(width):
                                new_data[i][j][0] = data[i][j * 6] << 8 |  data[i][j * 6 + 1]
                                new_data[i][j][1] = data[i][j * 6 + 2] << 8 |  data[i][j * 6 + 3]
                                new_data[i][j][2] = data[i][j * 6 + 4] << 8 |  data[i][j * 6 + 5]
                    case _:
                        logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
                        sys.exit(1)
            case 3:
                # palette index
                if palette is None:
                    logger.error('Palette is not found')
                    sys.exit(1)
                match bit_depth:
                    case 1 | 2 | 4 | 8:
                        new_data = np.ndarray(shape=(height, width, 3), dtype=np.uint8)
                        for i in range(height):
                            for j in range(width):
                                new_data[i][j] = palette[data[i][j]]
                    case _:
                        logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
                        sys.exit(1)
            case 4:
                # grayscale + alpha
                match bit_depth:
                    case 8:
                        data = data.reshape(height, width, 2)
                        r = g = b = data[:, :, 0] # grayscale
                        a = data[:, :, 1]         # alpha
                        new_data = np.dstack((r, g, b, a))
                    case 16:
                        new_data = np.ndarray(shape=(height, width, 4), dtype=np.uint16)
                        for i in range(height):
                            for j in range(width):
                                gray: np.uint16 = data[i][j * 4] << 8 |  data[i][j * 4 + 1]
                                alpha: np.uint16 = data[i][j * 4 + 2] << 8 |  data[i][j * 4 + 3]
                                new_data[i][j][0] = new_data[i][j][1] = new_data[i][j][2] = gray
                                new_data[i][j][3] = alpha
                    case _:
                        logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
                        sys.exit(1)
            case 6:
                # RGB + alpha
                if palette is not None:
                    logger.warning('Palette is found but color type is 6')
                match bit_depth:
                    case 8:
                        new_data = data.reshape(height, width, 4)
                    case 16:
                        new_data = np.ndarray(shape=(height, width, 4), dtype=np.uint16)
                        for i in range(height):
                            for j in range(width):
                                new_data[i][j][0] = data[i][j * 8] << 8 |  data[i][j * 8 + 1]
                                new_data[i][j][1] = data[i][j * 8 + 2] << 8 |  data[i][j * 8 + 3]
                                new_data[i][j][2] = data[i][j * 8 + 4] << 8 |  data[i][j * 8 + 5]
                                new_data[i][j][3] = data[i][j * 8 + 6] << 8 |  data[i][j * 8 + 7]
                    case _:
                        logger.error(f'{bit_depth} bit for color type {color_type} is not allowed')
                        sys.exit(1)
            case _:
                logger.error(f'Color type {color_type} is not allowed')
                sys.exit(1)

        assert new_data is not None

        logger.info('Finish generating color data successfully')
        return new_data

    # Restoring original image data from filtered image data is done byte by byte, not pixel by pixel.
    def _remove_filter(self, data: bytes, width: int, height: int, bytes_per_pixel: int, bit_depth: int) -> np.ndarray:
        logger.info('Start removing filter')
        match bit_depth:
            case 1 | 2 | 4:
                if bit_depth * width % 8 == 0:
                    bytes_per_line = bit_depth * width // 8
                else:
                    # All pixels in a scanline are packed into bytes without regard to the byte boundaries.
                    # If bit depth is less than 8, some low-order bits of the last byte of the scanline are not used (undefined value).
                    bytes_per_line = bit_depth * width // 8 + 1
                corr_byte_dist = 1
            case 8 | 16:
                bytes_per_line = width * bytes_per_pixel
                corr_byte_dist = bytes_per_pixel
            case _:
                logger.error(f'Bit depth {bit_depth} is not allowed')
                sys.exit(1)

        color_data = np.ndarray(shape=(height, bytes_per_line), dtype=np.uint8)

        for i in range(height):
            line_start_index = i * (1 + bytes_per_line)
            filter_type = data[line_start_index]
            data_start_index = line_start_index + 1

            match filter_type:
                case 0: # No filter
                    for j in range(bytes_per_line):
                        color_data[i][j] = data[data_start_index + j]
                case 1: # Sub filter
                    for j in range(bytes_per_line):
                        if j < corr_byte_dist:
                            pre = 0
                        else:
                            pre = color_data[i][j - corr_byte_dist]

                        color_data[i][j] = (data[data_start_index + j] + pre) % 256
                case 2: # Up filter
                    for j in range(bytes_per_line):
                        if i <= 0:
                            pre = 0
                        else:
                            pre = color_data[i - 1][j]

                        color_data[i][j] = (data[data_start_index + j] + pre) % 256
                case 3: # Average filter
                    for j in range(bytes_per_line):
                        if j >= corr_byte_dist and i > 0:
                            # The scanline is not the first scanline, and not the first pixel of the scanline
                            pre = int((color_data[i][j - corr_byte_dist]) + int(color_data[i - 1][j])) // 2
                        elif j >= corr_byte_dist:
                            # The scanline is the first scanline, but not the first pixel of the scanline
                            pre = color_data[i][j - corr_byte_dist] // 2
                        elif i > 0:
                            # The scanline is not the first scanline, but the first pixel of the scanline
                            pre = color_data[i - 1][j] // 2
                        else:
                            # The scanline is the first scanline, and the first pixel of the scanline
                            pre = 0

                        color_data[i][j] = (data[data_start_index + j] + pre) % 256
                case 4: # Paeth filter
                    for j in range(bytes_per_line):
                        a = int(color_data[i][j - corr_byte_dist]) if j >= corr_byte_dist else 0                # left
                        b = int(color_data[i - 1][j]) if i > 0 else 0                                           # upper
                        c = int(color_data[i - 1][j - corr_byte_dist]) if i > 0 and j >= corr_byte_dist else 0  # upper left

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

                        color_data[i][j] = (data[data_start_index + j] + pr) % 256
                case _:
                    logger.error(f'Filter type {filter_type} is not allowed')
                    sys.exit(1)

        logger.info('Finish removing filter successfully')
        return color_data

    def _get_bytes_per_pixel(self, color_type: int, bit_depth: int) -> int | float:
        match color_type:
            case 0:
                # grayscale
                bits_per_pixel = bit_depth
            case 2:
                # RGB
                bits_per_pixel = bit_depth * 3
            case 3:
                # palette index
                bits_per_pixel = bit_depth
            case 4:
                # grayscale + alpha
                bits_per_pixel = bit_depth * 2
            case 6:
                # RGB + alpha
                bits_per_pixel = bit_depth * 4
            case _:
                logger.error(f'Color type {color_type} is not allowed')
                sys.exit(1)

        if bits_per_pixel < 8:
            return bits_per_pixel / 8
        return int(bits_per_pixel / 8)

    def _is_valid_header(self, f: io.BufferedReader) -> bool:
        return f.read(8) == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A' # "HTJ P N G CR LF SUB LF"

    def _read_chunk(self, f: io.BufferedReader) -> tuple[int, str, bytes, int]:
        # Big endian
        chunk_length = int.from_bytes(f.read(4))
        chunk_type = f.read(4).decode('utf-8')
        chunk_data = f.read(chunk_length)
        chunk_crc = int.from_bytes(f.read(4))

        return chunk_length, chunk_type, chunk_data, chunk_crc

    def _read_IHDR(self, f: io.BufferedReader) -> tuple[int, int, int, int, int, int, int]:
        length, type, data, crc = self._read_chunk(f)
        calculated_crc32_checksum = crc32.calculate_crc32(type.encode('utf-8') + data)
        if calculated_crc32_checksum != crc:
            logger.error(f'Invalid CRC for chunk "{type}" (expected: {hex(crc)}, actual: {hex(calculated_crc32_checksum)})')
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
