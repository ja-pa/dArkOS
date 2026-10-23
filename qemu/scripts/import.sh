#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
check_import_space() {
 python3 "$QEMU_DIR/scripts/space.py" "$WORK_DIR" "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["input"]["image_size"]+1024**3)' "$RELEASE_LOCK")"
}
archive_dir=${ARCHIVE_DIR:-$REPO_DIR/images}
if [[ -n ${IMAGE:-} ]]; then
 [[ -f $IMAGE ]] || fail "Missing IMAGE=$IMAGE"
 [[ $(stat -c %s "$IMAGE") == $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["input"]["image_size"])' "$RELEASE_LOCK") ]] || fail 'Wrong image size'
 expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["input"].get("image_sha256", ""))' "$RELEASE_LOCK")
 [[ -n $expected ]] || fail 'Raw IMAGE requires image_sha256 in release lock; use verified archives for first import'
 echo "$expected  $IMAGE" | sha256sum -c -
 if [[ ! -e $RAW_IMAGE ]]; then check_import_space; cp --reflink=auto --sparse=always "$IMAGE" "$RAW_IMAGE.partial"; mv "$RAW_IMAGE.partial" "$RAW_IMAGE"; fi
else
 [[ -d $archive_dir ]] || fail "Set ARCHIVE_DIR to the archive volumes specified by RELEASE_LOCK=$RELEASE_LOCK (https://github.com/christianhaitian/dArkOS/releases)"
 python3 - "$RELEASE_LOCK" "$archive_dir" <<'PY' > "$WORK_DIR/state/archive.sha256"
import json,sys
from pathlib import Path
for a in json.load(open(sys.argv[1]))['input']['archives']:
 print(a['sha256']+'  '+str(Path(sys.argv[2]).resolve()/a['name']))
PY
 sha256sum -c "$WORK_DIR/state/archive.sha256" | tee "$WORK_DIR/logs/archive-verify.log"
 archive="$archive_dir/$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["input"]["archives"][0]["name"])' "$RELEASE_LOCK")"
 sevenzip=$(command -v 7zz || command -v 7z)
 "$sevenzip" t "$archive" > "$WORK_DIR/logs/archive-test.log"
 if [[ ! -e $RAW_IMAGE ]]; then
  check_import_space
  stage=$(mktemp -d "$WORK_DIR/images/.import.XXXXXX")
  "$sevenzip" x "$archive" "-o$stage" > "$WORK_DIR/logs/archive-extract.log"
  candidate=$stage/$(basename "$RAW_IMAGE")
  [[ $(stat -c %s "$candidate") == $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["input"]["image_size"])' "$RELEASE_LOCK") ]] || fail 'Unexpected extracted image size'
  mv "$candidate" "$RAW_IMAGE"; rmdir "$stage"
 fi
fi
sha256sum "$RAW_IMAGE" > "$WORK_DIR/state/base-image.sha256.partial"
expected_raw=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["input"].get("image_sha256", ""))' "$RELEASE_LOCK")
if [[ -n $expected_raw ]]; then
 [[ $(cut -d ' ' -f 1 "$WORK_DIR/state/base-image.sha256.partial") == "$expected_raw" ]] || fail 'Base image does not match the pinned release hash'
fi
if [[ -e $WORK_DIR/state/base-image.sha256 ]]; then cmp "$WORK_DIR/state/base-image.sha256" "$WORK_DIR/state/base-image.sha256.partial" || fail 'Base hash changed'; fi
mv "$WORK_DIR/state/base-image.sha256.partial" "$WORK_DIR/state/base-image.sha256"
chmod a-w "$RAW_IMAGE"
python3 - "$RELEASE_LOCK" "$WORK_DIR/state/base-image.sha256" <<'PY' > "$WORK_DIR/state/resolved-release.json"
import json,sys
v=json.load(open(sys.argv[1])); v['input']['image_sha256']=open(sys.argv[2]).read().split()[0]
print(json.dumps(v,indent=2))
PY
