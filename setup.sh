#!/bin/bash

set -eu

readonly VENV_DIR='.venv'

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip3 install -r requirements.txt
deactivate
