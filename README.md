# ppng

`ppng` is a simple PNG decoder built from scratch for educational purposes. It implements related algorithms like zlib, Deflate, Adler-32, and CRC-32 from the ground up without existing libraries.

## Features

`ppng` supports decoding of PNG images with all color types and bit depths.

### Color Type

- **Grayscale (color type 0)**
  - 1, 2, 4, 8, 16 bit

- **Truecolor (color type 2)**
  - 8, 16 bit

- **Indexed-color (color type 3)**
  - 1, 2, 4, 8 bit

- **Grayscale with alpha (color type 4)**
  - 8, 16 bit

- **Truecolor with alpha (color type 6)**
  - 8, 16 bit

It also supports some ancillary chunks.

### Ancillary Chunk

- `tEXt`
- `zTXt`
- `tIME`
- `gAMA`

## Usage

```text
Usage: bash run.sh [OPTIONS] FILE

Arguments:
  FILE  PNG file to decode  [required]

Options:
  -l, --logging  Enable logging
  --help         Show this message and exit.
```

Example:

```sh
bash run.sh -l tests/image/mandrill/type2-8bit.png
```

## Testing

```sh
bash tests/test.sh
```
