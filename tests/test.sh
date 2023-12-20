#!/bin/bash

set -eu

readonly VENV_DIR='../.venv'

if [ ! -d "$VENV_DIR" ]; then
    bash ../setup.sh
fi

source "$VENV_DIR/bin/activate"

python3 test_crc32.py

deactivate