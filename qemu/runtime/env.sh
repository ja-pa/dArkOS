#!/usr/bin/env bash
set -euo pipefail
export HOME=/home/ark XDG_CONFIG_HOME=/home/ark/.config
prefix=/opt/darkos-graphics
lib=$prefix/usr/lib/aarch64-linux-gnu
unset LD_PRELOAD GALLIUM_DRIVER MESA_LOADER_DRIVER_OVERRIDE EGL_PLATFORM
if [[ ${DARKOS_QEMU_CAPTURE:-0} == 1 ]]; then export LD_PRELOAD=/opt/darkos-qemu/capture.so; fi
export LD_LIBRARY_PATH=$lib
export LIBGL_DRIVERS_PATH=$lib/dri GBM_BACKENDS_PATH=$lib/gbm
export __EGL_VENDOR_LIBRARY_FILENAMES=$prefix/usr/share/glvnd/egl_vendor.d/50_mesa.json
export SDL_VIDEO_EGL_DRIVER=$lib/libEGL.so.1 SDL_VIDEO_GL_DRIVER=$lib/libOpenGL.so.0
export SDL_VIDEODRIVER=kmsdrm SDL_AUDIODRIVER=dummy SDL_OPENGL_ES_DRIVER=0
exec "$@"
