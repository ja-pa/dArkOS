#!/usr/bin/env bash
# Package an already prepared QEMU runtime; does not rebuild the guest.
set -euo pipefail
repo=$(cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$repo/qemu/release.py" "$@"
