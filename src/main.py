import time
from pathlib import Path

import typer
from rich.console import Console
from rich.traceback import install

import ppng

console = Console()
install(show_locals=True)

app = typer.Typer()


@app.command()
def run(
    file: Path = typer.Argument(
        ...,
        help="PNG file to decode",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    logging: bool = typer.Option(False, "-l", "--logging", help="Enable logging"),
) -> None:
    try:
        with open(file, "rb") as f:
            st = time.perf_counter()
            image = ppng.Decoder(is_logging=logging).decode_png(f)

        if logging:
            dt = time.perf_counter() - st
            console.print(f"Decoding time: {dt:.3f} sec")

        ppng.show_image(image, file.name)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(run)
