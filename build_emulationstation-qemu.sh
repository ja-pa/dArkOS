#!/usr/bin/env bash
# Release-image QEMU variation of the related upstream component recipe.
set -euo pipefail
if [[ ${QEMU_COMPONENT_BUILD:-} != guest ]]; then
 exec bash "$(dirname "$0")/qemu/build.sh" emulationstation
fi
 src=/opt/darkos-qemu/sources/emulationstation
 build=/opt/darkos-qemu/build/emulationstation
 cmake -S "$src" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DSDL_KMSDRM=ON -DGL=ON -DGLES=OFF -DCEC=OFF -DRPI=OFF \
  -DSDL2_INCLUDE_DIR="$prefix/usr/include/SDL2" -DSDL2_LIBRARY_TEMP="$lib/libSDL2.so" \
  -DOPENGL_gl_LIBRARY="$lib/libOpenGL.so" -DOPENGL_opengl_LIBRARY="$lib/libOpenGL.so" \
  -DOPENGL_glx_LIBRARY="$lib/libGLX.so" -DCMAKE_EXE_LINKER_FLAGS="-L$lib -Wl,-rpath-link,$lib" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
 cmake --build "$build" -j "${JOBS:-4}"
 cp "$build/emulationstation" "$out/$name/"
 cp -a "$src/resources" "$out/$name/"
 cp "$build/CMakeCache.txt" "$build/compile_commands.json" "$out/$name/"
