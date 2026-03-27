#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "Syncing dependencies (stats + dev)..."
uv sync --extra stats --extra dev

echo "Building onedir executable..."
uv run pyinstaller \
    --noconsole \
    --onedir \
    --name wotiti \
    --hidden-import=tkinter.filedialog \
    --collect-submodules sklearn \
    --collect-submodules scipy \
    --exclude-module torch \
    --add-data "src/assets:assets" \
    src/main.py

DIST_DIR="$REPO_ROOT/dist/wotiti"

if [ ! -d "$DIST_DIR" ]; then
    echo "ERROR: Build output not found: $DIST_DIR" >&2
    exit 1
fi

echo "Placing data/ next to executable..."
DATA_DST="$DIST_DIR/data"
if [ -d "$DATA_DST" ]; then
    rm -rf "$DATA_DST"
fi
cp -r "$REPO_ROOT/data" "$DATA_DST"

echo "Build complete: $DIST_DIR/wotiti"
