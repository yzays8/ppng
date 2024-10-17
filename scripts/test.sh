#!/bin/bash

set -eu
cd $(dirname $0)

readonly ROOT_DIR='..'
readonly VENV_DIR="$ROOT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    bash 'setup.sh'
fi

source "$VENV_DIR/bin/activate"
pytest "$ROOT_DIR/tests"
deactivate
