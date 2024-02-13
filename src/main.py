import sys
import os

import ppng

def main(argv: list[str]) -> int | None:
    def usage() -> None:
        print(f'usage: python3 {argv[0]} <file>')

    if len(argv) != 2:
        return usage()

    try:
        with open(argv[1], 'rb') as f:
            decoder = ppng.Decoder(is_logging=True)
            image = decoder.decode_png(f)
            ppng.show_image(image, os.path.basename(argv[1]))
        return
    except FileNotFoundError:
        print(f'File not found: {os.path.abspath(argv[1])}')
    except IsADirectoryError:
        print(f'Is a directory: {os.path.abspath(argv[1])}')
    except PermissionError:
        print(f'Permission denied: {os.path.abspath(argv[1])}')
    except Exception as e:
        print(e)
    return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
