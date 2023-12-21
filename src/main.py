import sys
import os

import pngd

def main(argv: list[str]) -> int | None:
    def usage():
        print(f'usage: python3 {argv[0]} <file>')
        return

    if len(argv) != 2:
        return usage()

    try:
        with open(argv[1], 'rb') as f:
            image = pngd.decode_png(f)
            pngd.show_image(image)
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
