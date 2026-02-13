#!/usr/bin/env bash

set -euo pipefail
cd $(dirname $0)

readonly ROOT_DIR=".."
readonly ORIG_IMAGE_PATH="$ROOT_DIR/tests/image/mandrill.tiff"
readonly DEST_DIR_PATH="$ROOT_DIR/tests/image/mandrill"

if [ ! -d $DEST_DIR_PATH ]; then
    mkdir $DEST_DIR_PATH
fi

## Color type
# 0: grayscale
# 2: truecolor
# 3: indexed-color
# 4: grayscale with alpha
# 6: truecolor with alpha

# Type 0, 1-bit
convert $ORIG_IMAGE_PATH -colorspace Gray -define png:color-type=0 -define png:bit-depth=1 "$DEST_DIR_PATH/type0-1bit.png"

# Type 0, 2-bit
convert $ORIG_IMAGE_PATH -colorspace Gray -define png:color-type=0 -define png:bit-depth=2 "$DEST_DIR_PATH/type0-2bit.png"

# Type 0, 4-bit
convert $ORIG_IMAGE_PATH -colorspace Gray -define png:color-type=0 -define png:bit-depth=4 "$DEST_DIR_PATH/type0-4bit.png"

# Type 0, 8-bit
convert $ORIG_IMAGE_PATH -colorspace Gray -define png:color-type=0 -define png:bit-depth=8 "$DEST_DIR_PATH/type0-8bit.png"

# Type 0, 16-bit
convert $ORIG_IMAGE_PATH -colorspace Gray -define png:color-type=0 -define png:bit-depth=16 "$DEST_DIR_PATH/type0-16bit.png"

# Type 2, 8-bit
convert $ORIG_IMAGE_PATH -define png:color-type=2 -define png:bit-depth=8 "$DEST_DIR_PATH/type2-8bit.png"

# Type 2, 16-bit
convert $ORIG_IMAGE_PATH -define png:color-type=2 -define png:bit-depth=16 "$DEST_DIR_PATH/type2-16bit.png"

# Type 3, 8-bit
convert $ORIG_IMAGE_PATH -define png:color-type=3 -define png:bit-depth=8 png8:"$DEST_DIR_PATH/type3-8bit.png"

# Type 4, 8-bit
convert $ORIG_IMAGE_PATH -colorspace Gray -define png:color-type=4 -define png:bit-depth=8 "$DEST_DIR_PATH/type4-8bit.png"

# Type 4, 16-bit
convert $ORIG_IMAGE_PATH -colorspace Gray -define png:color-type=4 -define png:bit-depth=16 "$DEST_DIR_PATH/type4-16bit.png"

# Type 6, 8-bit
convert $ORIG_IMAGE_PATH -define png:color-type=6 -define png:bit-depth=8 "$DEST_DIR_PATH/type6-8bit.png"

# Type 6, 16-bit
convert $ORIG_IMAGE_PATH -define png:color-type=6 -define png:bit-depth=16 "$DEST_DIR_PATH/type6-16bit.png"

# gamma 0.3
# These images are intended to be tested manually.
convert $ORIG_IMAGE_PATH -define png:color-type=2 -define png:bit-depth=8 +gamma 0.3 "$DEST_DIR_PATH/type2-8bit-gamma03.png"
convert $ORIG_IMAGE_PATH -define png:color-type=3 -define png:bit-depth=8 +gamma 0.3 png8:"$DEST_DIR_PATH/type3-8bit-gamma03.png"
