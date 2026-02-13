#!/usr/bin/env bash

set -euo pipefail
cd $(dirname $0)

readonly ROOT_DIR='..'
readonly VENV_DIR="$ROOT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip3 install -r "$ROOT_DIR/requirements.txt"
deactivate
