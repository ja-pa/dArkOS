#!/usr/bin/env bash
set -euo pipefail
[[ $(dpkg --print-architecture) == arm64 ]]
prefix=/opt/darkos-graphics
mkdir -p "$prefix" /opt/darkos-qemu/packages
cd /opt/darkos-qemu/packages
# Install build dependencies only on the disposable build disk. The runtime
# dependency closure is exported separately and installed without compilers.
if [[ -f build-package-debs.sha256 ]]; then
 sha256sum -c build-package-debs.sha256
 if [[ ! -f /opt/darkos-qemu/build-packages-applied ]]; then
  apt-get -y --no-download --no-install-recommends install "$PWD"/build/*.deb
 fi
elif [[ ! -f build-packages.lock ]]; then
 apt-get -o Acquire::Retries=3 update
 build=(build-essential cmake ninja-build pkg-config git ca-certificates libfreetype-dev libfreeimage-dev libsdl2-dev libsdl2-mixer-dev libcurl4-openssl-dev libvlc-dev rapidjson-dev libasound2-dev libudev-dev libdrm-dev libgbm-dev libegl-dev libgles-dev libgl-dev libopengl-dev libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libswresample-dev libpulse-dev zlib1g-dev libxml2-dev libssl-dev)
 apt-get -s --no-install-recommends install "${build[@]}" > build-apt-plan.txt
 ! grep -q '^Remv ' build-apt-plan.txt
 DEBIAN_FRONTEND=noninteractive apt-get -y -o Acquire::Retries=3 --no-install-recommends install "${build[@]}"
 dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' > build-packages.lock
fi

if [[ ! -f build-package-debs.sha256 ]]; then
 python3 - <<'PY' > build-changes.lock
from pathlib import Path
import subprocess
old={}
for block in Path('baseline-status').read_text().split('\n\n'):
    fields=dict(line.split(': ',1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
    if fields.get('Status')=='install ok installed': old[(fields['Package'],fields['Architecture'])]=fields['Version']
for line in subprocess.check_output(['dpkg-query','-W','-f=${Status}\t${Package}\t${Version}\t${Architecture}\n'],text=True).splitlines():
    status,name,version,arch=line.split('\t')
    if status!='install ok installed': continue
    if arch in ['arm64','armhf','all'] and old.get((name,arch))!=version:
        print(f'{name}:{arch}={version}')
PY
 mkdir -p build
 (cd build; xargs -r apt-get download < ../build-changes.lock)
 sha256sum build/*.deb > build-package-debs.sha256
fi
touch /opt/darkos-qemu/build-packages-applied

runtime=(libsdl2-2.0-0 libsdl2-mixer-2.0-0 libgbm1 libegl1 libgles2 libegl-mesa0 libgl1-mesa-dri mesa-libgallium libopengl0 libgl1 libglx0 libglx-mesa0 libglvnd0 libdrm2 libdrm-tests libfreeimage3 libfreetype6 libcurl4t64 libvlc5 libasound2t64 libudev1 libavcodec61 libavformat61 libavutil59 libswscale8 libswresample5)
runtime_request=$(printf '%s\n' "${runtime[@]}" | sha256sum | cut -d ' ' -f 1)
if [[ ! -f runtime-requests.sha256 || $(cat runtime-requests.sha256) != "$runtime_request" ]]; then
 mkdir -p runtime partial
 # APT resolves all dependencies against an empty status database, ensuring the
 # private prefix carries transitive dependencies missing from the release.
 apt-get -y -o Acquire::Retries=3 -o Dir::State::status=/dev/null -o Dir::Cache::archives="$PWD/runtime" --download-only --no-install-recommends install "${runtime[@]}"
 for deb in runtime/*.deb; do dpkg-deb -f "$deb" Package Version Architecture | paste - - -; done > runtime-packages.lock
 sha256sum runtime/*.deb > runtime-packages.sha256
 echo "$runtime_request" > runtime-requests.sha256
fi
sha256sum -c runtime-packages.sha256
for deb in runtime/*.deb; do dpkg-deb -x "$deb" "$prefix"; done
# Development files are build-only and must resolve graphics to this prefix.
mkdir -p dev
for p in libsdl2-dev libgbm-dev libegl-dev libgles-dev libgl-dev libopengl-dev libglx-dev; do
 v=$(apt-cache policy "$p:arm64" | awk '/Candidate:/ {print $2}')
 (cd dev; [[ -n $(find . -name "${p}_*.deb" -print -quit) ]] || apt-get download "$p:arm64=$v")
done
for deb in dev/*.deb; do dpkg-deb -x "$deb" "$prefix"; done
for lib in libSDL2.so libEGL.so libGLESv2.so libgbm.so libGL.so libOpenGL.so; do
 readelf -h "$prefix/usr/lib/aarch64-linux-gnu/$lib" | grep -q AArch64
 done
