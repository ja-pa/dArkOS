#!/usr/bin/env bash
# Keep G350 geometry/resources; select the upstream keyboard input branch.
set -euo pipefail
if [[ ${QEMU_COMPONENT_BUILD:-} != guest ]]; then
 exec bash "$(dirname "$0")/qemu/build.sh" 351files
fi
src=/opt/darkos-qemu/sources/351files
build=/opt/darkos-qemu/build/351files
# Do not reuse RG351MP object files or objects from a previous patch revision.
mkdir -p "$build"
tar -C "$src" --exclude=.git --exclude='*.o' --exclude=351Files -cf - . | tar -C "$build" -xf -
make -C "$build" clean
make -C "$build" -j "${JOBS:-4}" CC='g++ -O2' DEVICE=QEMU \
 SDL2_CONFIG='pkg-config sdl2' START_PATH=/roms RES_PATH=./res
cp "$build/351Files" "$out/$name/$name"
