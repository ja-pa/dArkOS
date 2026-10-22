#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
case ${1:-prepare} in
 prepare) python3 "$QEMU_DIR/scripts/portmaster.py" prepare;;
 upgrade)
  exec 9>"$WORK_DIR/state/pipeline.lock"
  flock -n 9 || fail 'Another pipeline owns WORK_DIR'
  # Offline upgrade requires the existing VM to be stopped.
  bash "$QEMU_DIR/vm.sh" check
  python3 "$QEMU_DIR/scripts/portmaster.py" prepare
  # Invalidate validation before any guest mutation, including a failed upgrade.
  rm -f "$WORK_DIR/state/image.json"
  with_disk "$DISK_IMAGE" rw bash "$0" --mounted
  ;;
 --mounted)
  mount "$ROMS_DEVICE" "$ROOT/roms"
  python3 "$QEMU_DIR/scripts/configure.py"
  python3 "$QEMU_DIR/scripts/portmaster.py" install
  ;;
 *) fail 'Usage: qemu/scripts/portmaster.sh [prepare|upgrade]';;
esac
