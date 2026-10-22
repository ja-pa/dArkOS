#!/usr/bin/env bash
set -euo pipefail
name=$1
gcc -O2 -shared -fPIC /opt/darkos-qemu/capture.c -ldl -o /opt/darkos-qemu/output/capture.so
mkdir -p /opt/darkos-qemu/output/"$name"
exec 3>&1 4>&2
exec > >(tee -a /opt/darkos-qemu/output/"$name"/build.log) 2>&1
log_tee=$!
finish_log() { local status=$?; exec 1>&3 2>&4; wait "$log_tee" || status=1; exit "$status"; }
trap finish_log EXIT
date -u +%FT%TZ
gcc --version | head -1
g++ --version | head -1
cmake --version | head -1
start=$SECONDS
prefix=/opt/darkos-graphics
lib=$prefix/usr/lib/aarch64-linux-gnu
export PKG_CONFIG_PATH=$lib/pkgconfig
export LD_LIBRARY_PATH=$lib
export LIBRARY_PATH=$lib
# Debian .pc files use an absolute /usr prefix; rewrite only our private copies.
for pc in "$lib"/pkgconfig/*.pc; do sed -i "s|^prefix=/usr$|prefix=$prefix/usr|" "$pc"; done
out=/opt/darkos-qemu/output
mkdir -p "$out/$name" /opt/darkos-qemu/build
export QEMU_COMPONENT_BUILD=guest
source /opt/darkos-qemu/build_"$name"-qemu.sh
binary=$out/$name/$name
readelf -h -d -V "$binary" > "$out/$name/elf.txt"
readelf -h "$binary" | grep -q AArch64
! readelf -d "$binary" | grep -Ei 'libmali|librga|libgo2'
! nm -D -u "$binary" | grep -Ei 'go2_|RkRga|rga_|mali_'
ldd "$binary" | tee "$out/$name/ldd.txt"
! grep -q 'not found' "$out/$name/ldd.txt"
sha256sum "$binary" > "$out/$name/binary.sha256"

printf "wall_seconds=%s\n" "$((SECONDS-start))" > "$out/$name/timing.txt"
