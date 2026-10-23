#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
[[ -e $WORK_DIR/images/build.qcow2 && -e $DISK_IMAGE ]] || python3 "$QEMU_DIR/scripts/space.py" "$WORK_DIR" $((6 * 1024**3))
[[ -s $WORK_DIR/state/profile.json ]] || fail 'Run qemu-inspect first'
# Provision capacity before DNS/APT, dependency installation or any compilation.
# The imported ROOTFS is too small for builds; grow both overlays on fresh setup.
if [[ ! -e $WORK_DIR/images/build.qcow2 ]]; then
 qemu-img create -f qcow2 -F raw -b "$RAW_IMAGE" "$WORK_DIR/images/build.qcow2"
fi
bash "$QEMU_DIR/scripts/grow.sh" "$WORK_DIR/images/build.qcow2" 12
# Runtime starts from the official image, never from the compiler-equipped build disk.
if [[ ! -e $DISK_IMAGE ]]; then qemu-img create -f qcow2 -F raw -b "$RAW_IMAGE" "$DISK_IMAGE"; fi

bash "$QEMU_DIR/scripts/grow.sh" "$DISK_IMAGE" 4

if [[ ! -e $SSH_KEY ]]; then ssh-keygen -q -t ed25519 -N '' -f "$SSH_KEY"; fi
with_disk "$WORK_DIR/images/build.qcow2" chroot bash "$QEMU_DIR/scripts/chroot-run.sh" -c 'set -e; test "$(dpkg --print-architecture)" = arm64; test -f /etc/debian_version; getent hosts deb.debian.org; apt-get -o Acquire::Retries=3 update; dpkg-query -W' > "$WORK_DIR/logs/chroot-preflight.log"
