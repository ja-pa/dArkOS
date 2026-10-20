#!/usr/bin/env bash
# Local privileged failure-path check against the disposable build overlay.
source "$(dirname "$0")/../lib.sh"
exec 9>"$WORK_DIR/state/pipeline.lock"
flock -n 9 || fail 'Stop the conversion pipeline before checking failure cleanup'
set +e
with_disk "$WORK_DIR/images/build.qcow2" ro bash -c 'cd "$ROOT"; sleep 120 & echo "$!" > "$WORK_DIR/state/cleanup-test.pid"; exit 7'
status=$?
set -e
[[ $status == 7 ]] || fail "Failure status lost: $status"
[[ -z $(find "$WORK_DIR" -maxdepth 1 -name '.mount.*' -print -quit) ]] || fail 'Leaked mount directory'
pid=$(cat "$WORK_DIR/state/cleanup-test.pid")
if [[ -f /proc/$pid/stat ]]; then
 state=$(awk '{print $3}' /proc/"$pid"/stat)
 [[ $state == Z ]] || fail 'A stage child survived cleanup'
fi
printf 'Failed-stage status, orphan termination and mount/NBD cleanup passed.\n'
