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
    /roms/ports/*.sh|/roms/ports/*.SH)
        # ES supplies the installed launcher's path, including spaces. Resolve it
        # before execution so traversal and symlinks cannot leave the ports tree.
        launcher=$(realpath -e -- "$1") || exit 2
        case "$launcher" in
            /roms/ports/*.sh|/roms/ports/*.SH) ;;
            *) echo 'Ports launcher resolves outside /roms/ports' >&2; exit 2;;
        esac
        [[ -f "$launcher" ]] || { echo 'Ports launcher is not a file' >&2; exit 2; }
        cd -- "$(dirname -- "$launcher")"
        exec bash /opt/darkos-qemu/env.sh bash "$launcher"
        ;;
    *) echo 'Unsupported Ports entry' >&2; exit 2;;
esac
