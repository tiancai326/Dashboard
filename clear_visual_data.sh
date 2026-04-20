#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python not found at $PYTHON_BIN"
  exit 1
fi

"$PYTHON_BIN" "$ROOT_DIR/backend/clear_visual_data.py" "$@"
