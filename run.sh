#!/bin/bash

set -eu
cd $(dirname $0)

readonly VENV_DIR='.venv'

if [ ! -d "$VENV_DIR" ]; then
    bash setup.sh
fi

source "$VENV_DIR/bin/activate"

if [[ -z "$@" ]]; then
    python3 src/main.py
else
    python3 src/main.py "$@"
fi
deactivate
