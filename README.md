# ppng

## Overview

ppng is a simple PNG decoder implemented from scratch at the level of zlib and DEFLATE algorithms.

## Support

ppng supports decoding of all PNG image formats except color type 0 (gray-scale) at bit depths of 1, 2, and 4 bits. It also supports tEXt, tIME, and gAMA as auxiliary chunks.

## Usage

```sh
bash run.sh <PNG image>
```
