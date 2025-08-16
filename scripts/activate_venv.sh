#!/usr/bin/env bash
# Activate the Python virtual environment for bash (Linux/macOS)
# Usage: source scripts/activate_venv.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_ACTIVATE="$SCRIPT_DIR/../venv/bin/activate"

if [ ! -f "$VENV_ACTIVATE" ]; then
  echo "Could not find venv activate script at '$VENV_ACTIVATE'. Ensure the virtual environment exists."
  return 1
fi

# Source the venv activate script so it affects the current shell
. "$VENV_ACTIVATE"
echo "Virtual environment activated."
