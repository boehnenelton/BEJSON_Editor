#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Script Name:    run.sh
# Description:    Shell launcher for BEJSON Editor Flask Async Manager
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/server_manager.py" "$@"
