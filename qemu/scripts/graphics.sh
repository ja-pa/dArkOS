#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
if [[ ${1:-} != --mounted ]]; then
 with_disk "$WORK_DIR/images/build.qcow2" chroot bash "$0" --mounted
 exit
fi
mkdir -p "$ROOT/opt/darkos-qemu" "$WORK_DIR/artifacts/graphics"
cp "$WORK_DIR/logs/inspect/dpkg-status" "$WORK_DIR/artifacts/graphics/baseline-status"
cp "$QEMU_DIR/scripts/graphics-guest.sh" "$ROOT/opt/darkos-qemu/graphics-guest.sh"
# Keep .deb files and resolved package metadata to avoid silent APT refreshes.
mount --bind "$WORK_DIR/artifacts/graphics" "$ROOT/opt/darkos-qemu/packages" 2>/dev/null || {
 mkdir -p "$ROOT/opt/darkos-qemu/packages"
 mount --bind "$WORK_DIR/artifacts/graphics" "$ROOT/opt/darkos-qemu/packages"
}
bash "$QEMU_DIR/scripts/chroot-run.sh" /opt/darkos-qemu/graphics-guest.sh
