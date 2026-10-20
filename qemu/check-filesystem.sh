#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
if [[ ${1:-} != --mounted ]]; then
 with_disk "${1:-$DISK_IMAGE}" ro bash "$0" --mounted
 exit
fi
[[ $ROOT_FSTYPE == btrfs ]] || fail 'Expected Btrfs'
umount "$ROOT"
btrfs check --readonly "$ROOT_DEVICE"
