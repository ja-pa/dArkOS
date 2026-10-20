#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
export ES_SYSROOT=$WORK_DIR/sdk/sysroot
python3 "$QEMU_DIR/scripts/workflow-sdk.py" check
source "$WORK_DIR/sdk/environment.sh"
case ${1:-help} in
 build)
  [[ $# == 2 ]] || fail 'Usage: qemu/app.sh build <CMake-source-directory>'
  src=$(realpath "$2"); name=$(basename "$src")
  cmake -S "$src" -B "$WORK_DIR/apps/$name" -G Ninja -DCMAKE_TOOLCHAIN_FILE="$QEMU_DIR/scripts/es-toolchain.cmake"
  cmake --build "$WORK_DIR/apps/$name" -j "${JOBS:-4}"
  ;;
 deploy)
  [[ $# == 2 && -f $2 ]] || fail 'Usage: qemu/app.sh deploy <ARM64-binary>'
  aarch64-linux-gnu-readelf -h "$2" | grep -q AArch64
  source "$QEMU_DIR/scripts/workflow-common.sh"
  vm verify
  sdk_match
  name=$(basename "$2"); [[ $name =~ ^[a-zA-Z0-9._-]+$ ]] || fail 'Unsafe binary filename'
  remote "sudo -n mkdir -p /opt/darkos-apps/$name"
  tar -C "$(dirname "$2")" -cf - "$name" | remote "sudo -n tar -C /opt/darkos-apps/$name -xf -"
  ;;
 *) fail 'Usage: qemu/app.sh build <CMake-source-directory>|deploy <ARM64-binary>';;
esac
