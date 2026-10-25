#!/usr/bin/env bash
# No lib.sh/pipeline: missing work directories must not be prepared implicitly.
source "$(dirname -- "$0")/common.sh"
umask 077
export DISK_IMAGE=${DISK_IMAGE:-$WORK_DIR/images/work.qcow2}
export KERNEL_IMAGE=${KERNEL_IMAGE:-$BUILD_DIR/arch/arm64/boot/Image}
export SSH_KEY=${SSH_KEY:-$WORK_DIR/ssh/id_ed25519}
export QMP_SOCKET=${QMP_SOCKET:-$WORK_DIR/state/qmp.sock}
exec python3 "$PROJECT_DIR/scripts/smoke.py" "$@"
