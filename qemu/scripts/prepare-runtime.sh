#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
if [[ ${1:-} != --mounted ]]; then
 with_disk "$DISK_IMAGE" rw bash "$0" --mounted
 exit
fi
mkdir -p "$ROOT/opt/darkos-qemu"
python3 "$QEMU_DIR/scripts/configure.py"
if [[ ! -f $ROOT/etc/ssh/ssh_host_ed25519_key.qemu-created ]]; then
 key=$ROOT/etc/ssh/ssh_host_ed25519_key
 rm -f "$key" "$key.pub"
 ssh-keygen -q -t ed25519 -N '' -f "$key"
 touch "$key.qemu-created"
fi
