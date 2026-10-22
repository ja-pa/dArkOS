#!/usr/bin/env bash
set -euo pipefail
QEMU_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
REPO_DIR=$(dirname "$QEMU_DIR")
export WORK_DIR=${WORK_DIR:-$HOME/darkos-g350-qemu}
WORK_DIR=$(realpath -m "$WORK_DIR")
[[ $WORK_DIR != / && $WORK_DIR != /home && $WORK_DIR != "$REPO_DIR" && $WORK_DIR != /mnt/* ]] || { echo 'WORK_DIR must be a dedicated native Linux directory' >&2; exit 1; }
export RELEASE_LOCK=${RELEASE_LOCK:-$QEMU_DIR/locks/g350-v01302026.json}
export RAW_IMAGE=$WORK_DIR/images/$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["input"]["image_filename"])' "$RELEASE_LOCK")
export SSH_PORT=${SSH_PORT:-2232}
export SSH_KEY=${SSH_KEY:-$WORK_DIR/ssh/id_ed25519}
export DISK_IMAGE=${DISK_IMAGE:-$WORK_DIR/images/work.qcow2}
export KERNEL_IMAGE=${KERNEL_IMAGE:-$WORK_DIR/build/arch/arm64/boot/Image}
export JOBS=${JOBS:-4}
mkdir -p "$WORK_DIR"/{images,logs,state,artifacts,ssh}
fail() { echo "Error: $*" >&2; exit 1; }
root() { if (( EUID == 0 )); then "$@"; else sudo -- "$@"; fi; }
with_disk() { root env WORK_DIR="$WORK_DIR" RELEASE_LOCK="$RELEASE_LOCK" JOBS="$JOBS" bash "$QEMU_DIR/scripts/with-disk.sh" "$@"; }
