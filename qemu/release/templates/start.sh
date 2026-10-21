#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")" && pwd)
command -v python3 >/dev/null || { echo 'Install python3 (see README.md)' >&2; exit 1; }
exec python3 "$root/scripts/release-vm.py" start "$@"
