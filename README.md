# ppng

## Overview

ppng is a simple PNG decoder built from scratch for educational purposes. It implements related algorithms like zlib, Deflate, CRC-32, and Adler-32 from the ground up without existing libraries.

## Support

ppng supports decoding of all PNG image formats.

- Grayscale (color type 0)
  - 1, 2, 4, 8, 16 bit

- Truecolor (color type 2)
  - 8, 16 bit

- Indexed-color (color type 3)
  - 1, 2, 4, 8 bit

- Grayscale with alpha (color type 4)
  - 8, 16 bit

- Truecolor with alpha (color type 6)
  - 8, 16 bit

It also supports `tEXt`, `zTXt`, `tIME`, and `gAMA` as ancillary chunks.

## Usage

```sh
bash run.sh [-l, --logging] <PNG image>
```

## Testing

```sh
bash tests/test.sh
```
