#!/bin/bash
set -e

# CD to the directory where this script is located
cd "$(dirname "$0")"

# Check if any file in directory was modified/created within last 10 seconds
has_recent_files() {
  local dir_path="$1"
  find "$dir_path" -type f -newermt "30 seconds ago" | head -1 | grep -q . && return 1 || return 0
}

HOME_DIR=$(eval echo ~$(whoami))
export PATH="$HOME_DIR/.local/bin:$PATH"

# Get arguments
DAILY_PATH="${1:-$HOME_DIR/daily}"
ANALYZER="${2:-grok}"

# the call returns 1 when there are some recently modified files, and due to `set -e` directive, the script will exit
has_recent_files "$DAILY_PATH"
uv run nutrition101/cli.py enrich-notes "$DAILY_PATH" n101 --analyzer="$ANALYZER"
