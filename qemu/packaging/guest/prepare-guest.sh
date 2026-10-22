#!/usr/bin/env bash
# Invoked only on the exported copy by with-disk.sh in its private mount namespace.
set -euo pipefail
source "$(dirname -- "$0")/../../scripts/sanitize.sh"
assets=$(cd -- "$(dirname -- "$0")" && pwd)
[[ -f $ROOT/opt/darkos-qemu/env.sh && -x $ROOT/opt/darkos-es/emulationstation ]]
install -m 755 "$assets/guest-start.sh" "$ROOT/opt/darkos-qemu/release-start.sh"
install -m 644 "$assets/../../scripts/audio-profile.py" "$ROOT/opt/darkos-qemu/audio-profile.py"
install -m 644 "$assets/darkos-release.service" "$ROOT/etc/systemd/system/darkos-release.service"
mkdir -p "$ROOT/etc/systemd/system/multi-user.target.wants" "$ROOT/etc/systemd/logind.conf.d"
ln -sfn ../darkos-release.service "$ROOT/etc/systemd/system/multi-user.target.wants/darkos-release.service"
for unit in ssh.service ssh.socket serial-getty@ttyAMA0.service; do
  ln -sfn /dev/null "$ROOT/etc/systemd/system/$unit"
done
printf '[Login]\nHandlePowerKey=poweroff\n' > "$ROOT/etc/systemd/logind.conf.d/qemu-release.conf"
find "$ROOT/home" "$ROOT/root" -type d -name .ssh -prune -exec rm -rf -- {} +
find "$ROOT/var/log" -type f -delete
find "$ROOT/home/ark" -type f \( -name es_log.txt -o -name es_log.txt.bak \) -delete
rm -f "$ROOT/var/lib/darkos-qemu/audio-v1.json" "$ROOT/var/lib/darkos-qemu/alsa-hda.state"
[[ -n $ROMS_DEVICE ]]
mkdir -p "$ROOT/roms"
mount "$ROMS_DEVICE" "$ROOT/roms"
find "$ROOT/roms" -type f \( -iname '*.srm' -o -iname '*.sav' -o -name '*.state' -o -name '*.state[0-9]*' \) -delete
sync
fstrim "$ROOT" || true
umount "$ROOT/roms"
