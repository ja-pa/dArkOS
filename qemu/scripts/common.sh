#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
release_settings=$(python3 "$PROJECT_DIR/scripts/release_config.py")
eval "$release_settings"
KERNEL_SRC=${KERNEL_SRC:-$WORK_DIR/kernel}
BUILD_DIR=${BUILD_DIR:-$WORK_DIR/build}
export SSH_PORT=${SSH_PORT:-2232}
if [[ -f $WORK_DIR/state/profile.env ]]; then source "$WORK_DIR/state/profile.env"; fi
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || fail "Missing dependency: $1 (see README.md)"; }
