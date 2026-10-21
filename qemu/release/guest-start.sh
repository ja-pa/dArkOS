#!/usr/bin/env bash
# Runs in the guest, never on the host.
set -euo pipefail
cd /opt/darkos-es
guest_home=/home/ark
wrapper=/opt/darkos-qemu/env.sh
udevadm settle --timeout=30
has_hda=false
for driver in /sys/class/sound/card*/device/driver; do
  [[ $(readlink -f "$driver") != */snd_hda_intel ]] || has_hda=true
done
if $has_hda; then
  python3 /opt/darkos-qemu/audio-profile.py --apply
else
  export SDL_AUDIODRIVER=dummy
fi
exec bash "$wrapper" ./emulationstation --home "$guest_home" --no-splash
