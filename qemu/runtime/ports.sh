#!/usr/bin/env bash
# All ES Ports entries share the QEMU graphics environment and launch log.
set -euo pipefail
[[ -f /etc/darkos-qemu-profile ]] || exit 1
mkdir -p /home/ark/.local/state/darkos-qemu
exec >>/home/ark/.local/state/darkos-qemu/ports.log 2>&1
printf '\n%s launch %s\n' "$(date -u +%FT%TZ)" "$*"
case ${1:-} in
    sdlpop|/roms/ports/SDLPoP.sh)
        cd /roms/ports/sdlpop
        # SDLPoP natively supports keyboard input. No mapper/board daemon needed.
        exec bash /opt/darkos-qemu/env.sh ./prince.aarch64
        ;;
    /roms/ports/PortMaster.sh)
        exec bash /opt/darkos-qemu/env.sh python3 /opt/darkos-qemu/portmaster-gui.py
        ;;
    /roms/ports/*.sh)
        echo "Port is not enabled in this QEMU pilot: $1" >&2
        echo 'Supported entries: PortMaster and SDLPoP.' >&2
        exit 2
        ;;
    *) echo 'Unsupported Ports entry' >&2; exit 2;;
esac
