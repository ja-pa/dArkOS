#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
exec 9>"$WORK_DIR/state/pipeline.lock"
flock -n 9 || fail 'Stop the pipeline before recording attestation'
exec python3 "$QEMU_DIR/scripts/attest.py"
