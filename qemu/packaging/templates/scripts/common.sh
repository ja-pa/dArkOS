#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
# Runtime settings belong to this copy, not an inherited development WORK_DIR.
WORK_DIR=$PROJECT_DIR/.runtime
BUILD_DIR=$PROJECT_DIR
KERNEL_IMAGE=$PROJECT_DIR/Image
DISK_IMAGE=$PROJECT_DIR/darkos.qcow2
QEMU_NO_SSH=1
export WORK_DIR KERNEL_IMAGE DISK_IMAGE QEMU_NO_SSH
read -r ROOT_PARTUUID ROOT_FSTYPE QEMU_MEMORY < <(python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["root_partuuid"],p["root_fstype"],p["memory_mb"])' "$PROJECT_DIR/config/image.json")
export ROOT_PARTUUID ROOT_FSTYPE QEMU_MEMORY
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || fail "Missing dependency: $1 (see release README.md)"; }
