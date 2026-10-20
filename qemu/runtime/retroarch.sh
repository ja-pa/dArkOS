#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: retroarch.sh core-name ROM' >&2; exit 2; }
core=/home/ark/.config/retroarch/cores/${1}_libretro.so
[[ -f $core && -f $2 ]] || exit 1
mkdir -p /home/ark/.config/retroarch/logs
exec bash /opt/darkos-qemu/env.sh /opt/retroarch/bin/retroarch \
 --config /home/ark/.config/retroarch/retroarch.qemu.cfg --verbose --log-file /home/ark/.config/retroarch/logs/last-run.log \
 -L "$core" "$2"
