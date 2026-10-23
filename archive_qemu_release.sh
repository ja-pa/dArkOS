#!/usr/bin/env bash
# Prepare uploadable assets from a verified standalone release.
set -euo pipefail
repo=$(cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$repo/qemu/packaging/archive.py" "$@"
