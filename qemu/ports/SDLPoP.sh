#!/usr/bin/env bash
# Same archive on QEMU and G350; retain the upstream hardware launcher.
set -e
if [[ -f /etc/darkos-qemu-profile ]]; then
    exec bash /opt/darkos-qemu/ports.sh sdlpop
fi
for base in /roms2/ports /roms/ports; do
    if [[ -f "$base/sdlpop/launch-handheld.txt" ]]; then
        exec bash "$base/sdlpop/launch-handheld.txt" "$@"
    fi
done
echo 'SDLPoP data directory not found' >&2
exit 1
