#!/usr/bin/env bash
source "$(dirname "$0")/scripts/lib.sh"
export ES_SYSROOT=$WORK_DIR/sdk/sysroot
refresh_launchers() {
 cp "$QEMU_DIR/scripts/sdk-environment.sh" "$WORK_DIR/sdk/environment.sh"
 cp "$QEMU_DIR/scripts/es-toolchain.cmake" "$WORK_DIR/sdk/toolchain.cmake"
}
case ${1:-help} in
 prepare)
  [[ $# == 1 ]] || fail 'Usage: sdk.sh prepare'
  mkdir -p "$WORK_DIR/sdk"
  [[ -s $WORK_DIR/state/runtime-id ]] || fail 'Package runtime before preparing SDK'
  if [[ -s $WORK_DIR/sdk/manifest.json ]] && python3 "$QEMU_DIR/scripts/workflow-sdk.py" check; then refresh_launchers; exit; fi
  if [[ -e $WORK_DIR/sdk/sysroot.partial ]]; then mv "$WORK_DIR/sdk/sysroot.partial" "$WORK_DIR/sdk/sysroot.interrupted.$(date +%s)"; fi
  with_disk "$WORK_DIR/images/build.qcow2" ro bash "$QEMU_DIR/sdk.sh" --mounted
  python3 "$QEMU_DIR/scripts/es-sysroot.py" "$WORK_DIR/sdk/sysroot.partial"
  [[ ! -e $ES_SYSROOT ]] || mv "$ES_SYSROOT" "$ES_SYSROOT.previous.$(date +%s)"
  mv "$WORK_DIR/sdk/sysroot.partial" "$ES_SYSROOT"
  cp "$WORK_DIR/state/runtime-id" "$WORK_DIR/sdk/runtime-id"
  refresh_launchers
  cp "$WORK_DIR/artifacts/graphics/build-packages.lock" "$WORK_DIR/sdk/packages.tsv"
  python3 "$QEMU_DIR/scripts/workflow-sdk.py" record
  python3 "$QEMU_DIR/scripts/workflow-sdk.py" check
  ;;
 --mounted)
  mkdir -p "$WORK_DIR/sdk/sysroot.partial"
  tar -C "$ROOT" -cf - usr/include usr/lib/aarch64-linux-gnu usr/lib/gcc usr/lib/pkgconfig lib opt/darkos-graphics/usr usr/share/pkgconfig usr/share/doc usr/share/common-licenses | tar -C "$WORK_DIR/sdk/sysroot.partial" -xf -
  chown -hR "$(stat -c %u "$WORK_DIR"):$(stat -c %g "$WORK_DIR")" "$WORK_DIR/sdk/sysroot.partial"
  chown "$(stat -c %u "$WORK_DIR"):$(stat -c %g "$WORK_DIR")" "$WORK_DIR/sdk"
  ;;
 check) python3 "$QEMU_DIR/scripts/workflow-sdk.py" check;;
 export|import) python3 "$QEMU_DIR/scripts/bundle.py" "$1-sdk" "$2";;
 *) echo 'Usage: qemu/sdk.sh prepare|check|export <directory>|import <directory>'; exit 2;;
esac
