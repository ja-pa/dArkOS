#!/usr/bin/env bash
set -euo pipefail
install -d -m 700 -o 1000 -g 1000 "$ROOT/home/ark/.ssh"
install -m 600 -o 1000 -g 1000 "$WORK_DIR/ssh/id_ed25519.pub" "$ROOT/home/ark/.ssh/authorized_keys"
key=$ROOT/etc/ssh/ssh_host_ed25519_key
[[ ! -f $key ]] || { echo 'Imported runtime still has a host key; expected sanitized bundle' >&2; exit 1; }
ssh-keygen -q -t ed25519 -N '' -f "$key"
touch "$key.qemu-created"
