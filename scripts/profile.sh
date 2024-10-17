#!/bin/bash

set -eu
cd $(dirname $0)
cd ..

readonly VENV_DIR='.venv'

if [ ! -d "$VENV_DIR" ]; then
    bash setup.sh
fi

source "$VENV_DIR/bin/activate"

cd src
if [[ -z "$@" ]]; then
    python3 -m cProfile --sort cumtime main.py
else
    python3 -m cProfile --sort cumtime main.py ../"$@"
fi
deactivate
