#!/usr/bin/env bash
# Guest only. Preserve runtime gcc-base packages, remove compiler executables.
set -euo pipefail
mkdir -p /opt/darkos-qemu
mapfile -t packages < <(dpkg-query -W -f='${Package}\n' | grep -E '^(gcc|g\+\+|cpp)(-[0-9]+)?(-aarch64-linux-gnu)?$|^(rustc|cargo)$' || true)
if (( ${#packages[@]} )); then
 apt-get -s purge "${packages[@]}" > /opt/darkos-qemu/compiler-removal-plan.log
 # Reject any unexpected removal outside the explicit compiler family.
 if grep -E '^(Remv|Purg) ' /opt/darkos-qemu/compiler-removal-plan.log | awk '{print $2}' | grep -Ev '^(gcc|g\+\+|cpp)(-[0-9]+)?(-aarch64-linux-gnu)?$|^(rustc|cargo|libtool|libtool-bin|x11-xserver-utils)$'; then
  echo 'Unexpected compiler-removal dependency; inspect the plan' >&2; exit 1
 fi
 DEBIAN_FRONTEND=noninteractive apt-get -y --no-download purge "${packages[@]}"
fi
for tool in gcc gcc-12 gcc-14 g++ cc c++ rustc cargo; do
 if command -v "$tool" >/dev/null; then echo "Compiler remains in runtime: $tool" >&2; exit 1; fi
done
