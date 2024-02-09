def check_adler32(data: bytes, adler32: int) -> bool:
    calc_adler32 = calculate_adler32(data)
    if calc_adler32 != adler32:
        print(f'Invalid Adler-32 checksum (expected: {hex(adler32)}, actual: {hex(calc_adler32)})')
        return False
    return True

def calculate_adler32(data: bytes) -> int:
    s1 = 1
    s2 = 0
    for byte in data:
        s1 = (s1 + byte) % 65521
        s2 = (s2 + s1) % 65521
    return (s2 << 16) | s1