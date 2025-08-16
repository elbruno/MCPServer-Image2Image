#!/usr/bin/env bash
# Deactivate the Python virtual environment for bash (Linux/macOS)
# Usage: deactivate_venv.sh can be run after activation; it's a convenience wrapper
# Recommended: use the builtin 'deactivate' function that comes from activating the venv.

# If deactivate function exists, call it
if type deactivate >/dev/null 2>&1; then
  deactivate
  echo "Virtual environment deactivated."
  return 0 2>/dev/null || exit 0
fi

# If deactivate isn't available, try to find the venv and source its deactivate if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DEACTIVATE="$SCRIPT_DIR/../venv/bin/deactivate"

if [ -f "$VENV_DEACTIVATE" ]; then
  . "$VENV_DEACTIVATE"
  echo "Virtual environment deactivated."
  return 0 2>/dev/null || exit 0
fi

echo "No active virtual environment detected (no 'deactivate' function)." >&2
return 1 2>/dev/null || exit 1
