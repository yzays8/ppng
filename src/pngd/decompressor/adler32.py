def calculate_adler32(data: bytes) -> int:
    s1 = 1
    s2 = 0
    for byte in data:
        s1 = (s1 + byte) % 65521
        s2 = (s2 + s1) % 65521
    return (s2 << 16) | s1
