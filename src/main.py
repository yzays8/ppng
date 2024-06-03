import os
import time

import typer

import ppng


def main(
    file: str = typer.Argument(..., help="PNG file to decode"),
    is_logging: bool = typer.Option(False, "-l", "--logging", help="Enable logging"),
) -> None:
    try:
        with open(file, "rb") as f:
            start = time.time()
            image = ppng.Decoder(is_logging=is_logging).decode_png(f)
            if is_logging:
                print(f"Decoding time: {time.time() - start:.3f} sec")
            ppng.show_image(image, os.path.basename(file))
        return
    except FileNotFoundError:
        print(f"File not found: {os.path.abspath(file)}")
    except IsADirectoryError:
        print(f"Is a directory: {os.path.abspath(file)}")
    except PermissionError:
        print(f"Permission denied: {os.path.abspath(file)}")
    except Exception as e:
        print(e)


if __name__ == "__main__":
    typer.run(main)
