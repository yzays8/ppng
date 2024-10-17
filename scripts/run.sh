#!/bin/bash

set -eu

# Convert all relative paths inside the arguments to absolute paths.
args=()
for arg in "$@"; do
    if [[ -f $arg || -d $arg ]]; then
        args+=("$(realpath "$arg")")
    else
        args+=("$arg")
    fi
done

cd $(dirname $0)

readonly ROOT_DIR='..'
readonly VENV_DIR="$ROOT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    bash 'setup.sh'
fi

source "$VENV_DIR/bin/activate"
python3 "$ROOT_DIR/src/main.py" ${args[@]}
deactivate
