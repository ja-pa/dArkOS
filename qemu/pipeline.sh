#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
exec 9>"$WORK_DIR/state/pipeline.lock"
flock -n 9 || fail 'Another pipeline owns WORK_DIR'
requested=${1:-all}
case $requested in import|inspect|prepare|graphics|build|image|test|sdk|all) ;; *) fail 'Unknown stage';; esac
previous=
run_stage() {
 local stage=$1; shift
 local receipt=$WORK_DIR/state/$stage.json
 if ! python3 "$QEMU_DIR/state.py" check "$QEMU_DIR" "$RELEASE_LOCK" "$receipt" "$previous"; then
  rm -f "$receipt"
  bash "$QEMU_DIR/$stage.sh" |& tee "$WORK_DIR/logs/$stage.log"
  python3 "$QEMU_DIR/state.py" record "$QEMU_DIR" "$RELEASE_LOCK" "$receipt" "$previous" "$@"
 fi
 previous=$receipt
}
run_stage import "$WORK_DIR/state/resolved-release.json" "$WORK_DIR/state/base-image.sha256" "$RAW_IMAGE"
[[ $requested != import ]] || exit 0
run_stage inspect "$WORK_DIR/state/profile.json" "$WORK_DIR/logs/inspect/files.json" "$WORK_DIR/logs/inspect/elf.json"
python3 "$QEMU_DIR/components.py" --lock "$RELEASE_LOCK" --work-dir "$WORK_DIR" --output "$WORK_DIR/logs/components.md"
[[ $requested != inspect ]] || exit 0
run_stage prepare "$WORK_DIR/logs/chroot-preflight.log"
[[ $requested != prepare ]] || exit 0
[[ -f $WORK_DIR/images/build.qcow2 && -f $DISK_IMAGE ]] || fail 'Working disks missing; remove prepare receipt and rerun'
run_stage graphics "$WORK_DIR/artifacts/graphics/runtime-packages.lock" "$WORK_DIR/artifacts/graphics/runtime-packages.sha256" "$WORK_DIR/artifacts/graphics/build-package-debs.sha256"
(cd "$WORK_DIR/artifacts/graphics"; sha256sum -c runtime-packages.sha256 > /dev/null)
[[ $requested != graphics ]] || exit 0
# Component requests use separate receipts to avoid marking the other build complete.
for component in emulationstation retroarch 351files; do
 [[ $requested != build || -z ${COMPONENT:-} || ${COMPONENT:-} == all || $COMPONENT == "$component" ]] || continue
 receipt=$WORK_DIR/state/build-$component.json
 if ! python3 "$QEMU_DIR/state.py" check "$QEMU_DIR" "$RELEASE_LOCK" "$receipt" "$previous"; then
  rm -f "$receipt"
  bash "$QEMU_DIR/build.sh" "$component" |& tee "$WORK_DIR/logs/build-$component.log"
  python3 "$QEMU_DIR/state.py" record "$QEMU_DIR" "$RELEASE_LOCK" "$receipt" "$previous" "$WORK_DIR/artifacts/$component/$component"
 fi
 # Component build receipts depend on graphics, not on the component selection/order.
done
[[ $requested != build ]] || exit 0
previous=$WORK_DIR/state/graphics.json
run_stage kernel "$KERNEL_IMAGE" "$WORK_DIR/build/.config" "$WORK_DIR/artifacts/kernel-source.json"
sha256sum "$WORK_DIR/state/kernel.json" "$WORK_DIR/state/build-emulationstation.json" "$WORK_DIR/state/build-retroarch.json" "$WORK_DIR/state/build-351files.json" > "$WORK_DIR/state/image-inputs.sha256"
previous=$WORK_DIR/state/image-inputs.sha256
run_stage image "$WORK_DIR/state/runtime-id" "$WORK_DIR/artifacts/delta.json"
[[ $requested != image ]] || exit 0
if [[ $requested == sdk ]]; then bash "$QEMU_DIR/sdk.sh" prepare; exit; fi
bash "$QEMU_DIR/test.sh"
