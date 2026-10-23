#!/usr/bin/env bash
# Release-image QEMU variation of the related upstream component recipe.
set -euo pipefail
if [[ ${QEMU_COMPONENT_BUILD:-} != guest ]]; then
 exec bash "$(dirname "$0")/qemu/scripts/build.sh" retroarch
fi
 # Keep a writable source copy on the build disk; never apply Rockchip patches.
 src=/opt/darkos-qemu/sources/retroarch
 build=/opt/darkos-qemu/build/retroarch
 source_commit=$(git -c safe.directory="$src" -C "$src" rev-parse HEAD)
 if [[ -e $build/configure && ( ! -f $build/.qemu-source-commit || $(cat "$build/.qemu-source-commit") != "$source_commit" ) ]]; then
  mv "$build" "$build.previous.$(date +%s)"
 fi
 if [[ ! -e $build/configure ]]; then mkdir -p "$build"; tar -C "$src" --exclude=.git -cf - . | tar -C "$build" -xf -; fi
 printf '%s\n' "$source_commit" > "$build/.qemu-source-commit"
 cd "$build"
 for file in config.h config.mk; do [[ ! -f $file ]] || cp -p "$file" "$file.before-qemu"; done
 CFLAGS='-O2 -march=armv8-a' CXXFLAGS='-O2 -march=armv8-a' LDFLAGS="-L$lib -Wl,-rpath-link,$lib" ./configure \
  --disable-odroidgo2 --disable-mali_fbdev --disable-vg --disable-vulkan --disable-vulkan_display \
  --disable-x11 --disable-wayland --disable-qt --disable-sdl --enable-sdl2 --enable-opengl \
  --disable-opengl_core --disable-opengles --enable-egl --enable-kms --enable-udev \
  --enable-freetype --enable-networking --enable-ozone --enable-alsa \
  --disable-jack --disable-pulse --disable-microphone
 for file in config.h config.mk; do
  if [[ -f $file.before-qemu ]] && cmp -s "$file" "$file.before-qemu"; then touch -r "$file.before-qemu" "$file"; fi
 done
 make -j "${JOBS:-4}"
 cp retroarch config.log config.mk "$out/$name/"
