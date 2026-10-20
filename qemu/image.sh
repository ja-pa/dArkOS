#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
if [[ ${1:-} != --mounted ]]; then
 [[ -s $WORK_DIR/artifacts/emulationstation/emulationstation && -s $WORK_DIR/artifacts/retroarch/retroarch && -s $WORK_DIR/artifacts/351files/351files ]] || fail 'Build all components before packaging'
 python3 "$QEMU_DIR/test-roms.py"
 bash "$QEMU_DIR/grow.sh" "$DISK_IMAGE" 4
 with_disk "$DISK_IMAGE" chroot bash "$0" --mounted
 qemu-img check "$DISK_IMAGE"
 exit
fi
mkdir -p "$ROOT/opt/darkos-qemu" "$ROOT/opt/darkos-graphics" "$ROOT/opt/darkos-es/scripts"
sha256sum -c "$WORK_DIR/artifacts/graphics/runtime-packages.sha256" --ignore-missing >/dev/null 2>&1 || (cd "$WORK_DIR/artifacts/graphics"; sha256sum -c runtime-packages.sha256)
for deb in "$WORK_DIR"/artifacts/graphics/runtime/*.deb; do dpkg-deb -x "$deb" "$ROOT/opt/darkos-graphics"; done
cp "$WORK_DIR/artifacts/emulationstation/emulationstation" "$ROOT/opt/darkos-es/"
cp -a "$WORK_DIR/artifacts/emulationstation/resources" "$ROOT/opt/darkos-es/"
cp "$WORK_DIR/artifacts/351files/351files" "$ROOT/opt/darkos-qemu/351Files"
cp "$WORK_DIR/artifacts/capture.so" "$ROOT/opt/darkos-qemu/capture.so"
cp "$WORK_DIR/artifacts/retroarch/retroarch" "$ROOT/opt/retroarch/bin/retroarch"
# Original paths remain valid for tools referring directly to the frontend.
cp "$WORK_DIR/artifacts/emulationstation/emulationstation" "$ROOT/usr/bin/emulationstation/emulationstation"
cp "$QEMU_DIR/runtime/env.sh" "$ROOT/opt/darkos-es/scripts/es-env.sh"
bash "$QEMU_DIR/prepare-runtime.sh" --mounted
cp "$QEMU_DIR/strip-compilers.sh" "$ROOT/opt/darkos-qemu/strip-compilers.sh"
bash "$QEMU_DIR/chroot-run.sh" /opt/darkos-qemu/strip-compilers.sh
mkdir -p "$ROOT/roms"
mount "$ROMS_DEVICE" "$ROOT/roms"
[[ -z $BOOT_DEVICE ]] || mount -o ro "$BOOT_DEVICE" "$ROOT/boot"
python3 "$QEMU_DIR/install-test-roms.py"
# Fingerprint the exact libraries and binaries used by the runtime and SDK.
{
 sha256sum "$WORK_DIR/artifacts/graphics/runtime-packages.sha256"
 sha256sum "$WORK_DIR/artifacts/emulationstation/emulationstation" "$WORK_DIR/artifacts/retroarch/retroarch" "$WORK_DIR/artifacts/351files/351files"
 cat "$WORK_DIR/state/base-image.sha256"
} | sha256sum | cut -d ' ' -f 1 > "$WORK_DIR/state/runtime-id"
cp "$WORK_DIR/state/runtime-id" "$ROOT/opt/darkos-graphics/runtime-id"
python3 "$QEMU_DIR/manifest.py"
sync
