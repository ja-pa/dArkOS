#!/usr/bin/env bash
source "$(dirname "$0")/scripts/lib.sh"
case ${1:-help} in
 source) exec bash "$QEMU_DIR/scripts/pipeline.sh" image;;
 import)
  [[ $# == 2 ]] || fail 'Usage: qemu/setup.sh import <runtime-bundle>'
  mkdir -p "$WORK_DIR/ssh"
  [[ -f $SSH_KEY ]] || ssh-keygen -q -t ed25519 -N '' -f "$SSH_KEY"
  python3 "$QEMU_DIR/scripts/bundle.py" import-runtime "$2"
  with_disk "$DISK_IMAGE" rw bash "$QEMU_DIR/scripts/import-identity.sh"
  ;;
 *) echo 'Usage: qemu/setup.sh source|import <runtime-bundle>'; exit 2;;
esac
