#!/usr/bin/env bash
# Explicit local checks; no package installation, ARM64 builds or guest boot.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
while IFS= read -r -d '' script; do bash -n "$script"; done < <(find qemu -name '*.sh' -print0)
for script in build_qemu.sh build_emulationstation-qemu.sh build_retroarch-qemu.sh build_351files-qemu.sh; do
 bash -n "$script"
done
scratch=$(mktemp -d)
trap 'rm -f "$scratch/capture.so"; rmdir "$scratch"' EXIT
gcc -Wall -Wextra -Werror -shared -fPIC qemu/capture.c -ldl -o "$scratch/capture.so"
python3 -m compileall -q qemu
python3 -m unittest discover -s qemu/tests -p 'test_*.py'
