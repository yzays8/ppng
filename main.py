import sys

from decoder import decode_png

def main(argv: list[str]) -> int | None:
    def usage():
        print(f'usage: {argv[0]} <file>')
        return

    if len(argv) != 2:
        return usage()

    try:
        with open(argv[1], 'rb') as f:
            decode_png(f)
        return
    except FileNotFoundError:
        print(f'File not found: {argv[1]}')
    except PermissionError:
        print(f'Permission denied: {argv[1]}')
    except Exception as e:
        print(e)
    return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
