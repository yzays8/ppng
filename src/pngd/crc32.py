def check_crc32(type: str, data: bytes, crc: int) -> bool:
    # CRC32 checksum for PNG chunks is calculated from the chunk type and chunk data.
    # 4 bytes 0x00 is appended to the end of the data to ensure that the data is longer than the polynomial.
    orig_data = type.encode('utf-8') + data + b'\x00' * 4

    # x32 + x26 + x23 + x22 + x16 + x12 + x11 + x10 + x8 + x7 + x5 + x4 + x2 + x + 1
    POLY = 0xEDB88320

    calc_crc = 0x00000000

    for i, byte in enumerate(orig_data):
        # Invert the first 4 bytes to prevent them from being ignored if they are 0x00.
        if i < 4:
            byte ^= 0xFF

        # The data is poured in from the MSB of calc_crc.
        for _ in range(8):
            flag = calc_crc & 1 == 1
            calc_crc >>= 1
            if byte & 1 == 1:
                calc_crc |= 0x80000000
            byte >>= 1
            if flag:
                calc_crc ^= POLY
    calc_crc ^= 0xFFFFFFFF

    if calc_crc != crc:
        print(f'Invalid CRC for chunk "{type}" (expected: {hex(crc)}, actual: {hex(calc_crc)})')
        return False
    return True
