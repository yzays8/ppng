# https://www.w3.org/TR/png-3/#5CRC-algorithm
def calculate_crc32(data: bytes) -> int:
    # The CRC polynomial employed is x32 + x26 + x23 + x22 + x16 + x12 + x11 + x10 + x8 + x7 + x5 + x4 + x2 + x + 1,
    # which is represented in binary as 0000 0100 1100 0001 0001 1101 1011 0111, and in hexadecimal as 0x04C11DB7.
    # This algorithm uses the inverted version, represented in binary as 1110 1101 1011 1000 1000 0011 0010 0000 and in hex as 0xEDB88320,
    # because each byte is processed in LSB to MSB.
    POLYNOMIAL = 0xEDB88320

    # The 32-bit CRC is initialized to all 1's in PNG.
    crc = 0xFFFFFFFF

    # The byte is taken from the top of the data.
    for byte in data:
        crc ^= byte
        # The byte is processed LSB to MSB in PNG.
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ POLYNOMIAL
            else:
                crc >>= 1

    # The CRC is inverted after all bytes have been processed in PNG.
    return crc ^ 0xFFFFFFFF
