#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
if [[ ${1:-} == --mounted ]]; then
 name=$2
 mkdir -p "$ROOT/opt/darkos-qemu" "$ROOT/opt/darkos-qemu/sources" "$ROOT/opt/darkos-qemu/output"
 mount --bind "$WORK_DIR/sources" "$ROOT/opt/darkos-qemu/sources"
 mount --bind "$WORK_DIR/artifacts" "$ROOT/opt/darkos-qemu/output"
 cp "$QEMU_DIR/build-guest.sh" "$ROOT/opt/darkos-qemu/build-guest.sh"
 cp "$QEMU_DIR/capture.c" "$ROOT/opt/darkos-qemu/capture.c"
 cp "$REPO_DIR/build_emulationstation-qemu.sh" "$REPO_DIR/build_retroarch-qemu.sh" "$REPO_DIR/build_351files-qemu.sh" "$ROOT/opt/darkos-qemu/"
 bash "$QEMU_DIR/chroot-run.sh" /opt/darkos-qemu/build-guest.sh "$name"
 exit
fi
git() { command git -c safe.directory="$WORK_DIR/sources/emulationstation" -c safe.directory="$WORK_DIR/sources/retroarch" -c safe.directory="$WORK_DIR/sources/351files" "$@"; }
component=${1:-all}
[[ $component == all || $component == emulationstation || $component == retroarch || $component == 351files ]] || fail 'COMPONENT must be emulationstation|retroarch|351files|all'
for name in emulationstation retroarch 351files; do
 [[ $component == all || $component == "$name" ]] || continue
 readarray -t source_info < <(python3 - "$RELEASE_LOCK" "$name" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]))['sources'][sys.argv[2]]
print(s['repo']+'.git'); print(s['commit'])
PY
 )
 src=$WORK_DIR/sources/$name
 if [[ ! -d $src/.git ]]; then
  mkdir -p "$src"; git -C "$src" init; git -C "$src" remote add origin "${source_info[0]}"
  git -C "$src" fetch --depth=1 origin "${source_info[1]}"; git -C "$src" checkout --detach FETCH_HEAD
 fi
 [[ $(git -C "$src" rev-parse HEAD) == "${source_info[1]}" ]] || fail "Wrong source commit for $name"
 if [[ -d $QEMU_DIR/patches/$name ]]; then
  for patch in "$QEMU_DIR/patches/$name"/*.patch; do
   if ! git -C "$src" apply --reverse --check "$patch" 2>/dev/null; then git -C "$src" apply --check "$patch"; git -C "$src" apply "$patch"; fi
  done
 fi
 if [[ $name == emulationstation ]]; then git -C "$src" submodule update --init --recursive --depth=1; fi
 with_disk "$WORK_DIR/images/build.qcow2" chroot bash "$QEMU_DIR/build.sh" --mounted "$name"
done
