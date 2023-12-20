#!/bin/bash

set -eu

readonly VENV_DIR='.venv'

if [ ! -d "$VENV_DIR" ]; then
    bash setup.sh
fi

source "$VENV_DIR/bin/activate"

cd src
if [[ -z "$@" ]]; then
    python3 main.py
else
    python3 main.py ../"$@"
fi
deactivate
