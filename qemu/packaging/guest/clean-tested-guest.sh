#!/usr/bin/env bash
# Only the temporary publishing copy is mounted by with-disk.sh.
set -euo pipefail
source "$(dirname -- "$0")/../../scripts/sanitize.sh"
find "$ROOT/home" "$ROOT/root" -type d -name .ssh -prune -exec rm -rf -- {} +
find "$ROOT/var/log" -type f -delete
if [[ -d $ROOT/opt/darkos-qemu ]]; then
  find "$ROOT/opt/darkos-qemu" -type f -name "*.log" -delete
fi
find "$ROOT/home/ark" -type f \( -name es_log.txt -o -name es_log.txt.bak \) -delete
[[ -n $ROMS_DEVICE ]]
mkdir -p "$ROOT/roms"
mount "$ROMS_DEVICE" "$ROOT/roms"
# Same save extensions as the original exporter; add SDLPoP's quicksave.
find "$ROOT/roms" -type f \( -iname '*.srm' -o -iname '*.sav' -o -name '*.state' -o -name '*.state[0-9]*' -o -name 'quicksave.sav' \) -delete
sync
fstrim "$ROOT" || true
umount "$ROOT/roms"
