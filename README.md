# ppng

## Overview

ppng is a simple PNG decoder implemented from scratch, including all related algorithms (zlib, Deflate, CRC-32, Adler-32).

## Support

ppng supports decoding of all PNG image formats.

- Greyscale (color type 0) - 1, 2, 4, 8, 16 bit
- Truecolor (color type 2) - 8, 16 bit
- Indexed-color (color type 3) - 1, 2, 4, 8 bit
- Grayscale with alpha (color type 4) - 8, 16 bit
- Truecolor with alpha (color type 6) - 8, 16 bit

It also supports `tEXt`, `zTXt`, `tIME`, and `gAMA` as auxiliary chunks.

## Usage

```sh
bash run.sh <PNG image>
```
