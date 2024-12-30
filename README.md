# ppng

ppng is a simple PNG decoder built from scratch for educational purposes. It implements related algorithms like zlib, Deflate, Adler-32, and CRC-32 from the ground up without existing libraries.

## Features

ppng supports all [color types](https://www.w3.org/TR/png-3/#3colourType) and [bit depths](https://www.w3.org/TR/png-3/#table111).

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

It also supports some [ancillary chunks](https://www.w3.org/TR/png-3/#3ancillaryChunk).

### Ancillary Chunk

- `tEXt`
- `zTXt`
- `iTXt`
- `tIME`
- `gAMA`

## Usage

```text
Usage: main.py [OPTIONS] FILE

Arguments:
  FILE  PNG file to decode  [required]

Options:
  -l, --logging  Enable logging
  --help         Show this message and exit.
```

### Example

You can easily run the program using a provided script.

```sh
bash scripts/run.sh -l tests/image/mandrill/type2-8bit.png
```

## Testing

Run the following command:

```sh
bash scripts/test.sh
```

PNG images for testing are included in this repo, but you can also generate them yourself from the TIFF file. Make sure that `ImageMagick` is installed on your system to execute `convert` command, and then run the following command:

```sh
bash scripts/generate_test_images.sh
```
