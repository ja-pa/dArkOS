"""QEMU launch adapter. Keep the downloaded PortMaster and board hooks intact."""
import os
from pathlib import Path
import runpy
import subprocess
import sys
import zipfile

if not Path('/etc/darkos-qemu-profile').is_file():
    raise SystemExit('Requires the QEMU profile')
pm = Path('/opt/tools/PortMaster')
os.chdir(pm)
archive = pm / 'pylibs.zip'
if archive.is_file():
    with zipfile.ZipFile(archive) as z:
        z.extractall(pm)
    archive.unlink()
lib = '/opt/darkos-graphics/usr/lib/aarch64-linux-gnu'
os.environ.update(
    PORTMASTER_HOME=str(pm), controlfolder=str(pm),
    HM_TOOLS_DIR='/opt/tools', HM_PORTS_DIR='/roms/ports', HM_SCRIPTS_DIR='/roms/ports',
    PYSDL2_DLL_PATH=lib, CFW_NAME='darkos-qemu', CFW_VERSION='G350 QEMU',
    CFW_GLIBC=subprocess.check_output(['getconf', 'GNU_LIBC_VERSION'], text=True).split()[-1],
    DEVICE_NAME='QEMU ARM64', DEVICE_CPU='QEMU TCG', DEVICE_ARCH='aarch64',
    DEVICE_RAM_MB=str(int(Path('/proc/meminfo').read_text().split('MemTotal:')[1].split()[0]) // 1024),
    DISPLAY_WIDTH='640', DISPLAY_HEIGHT='480', DISPLAY_ORIENTATION='0',
    ANALOG_STICKS='0', GPU_DRIVER='Mesa VirtIO',
    DEVICE_CAPABILITIES='aarch64 640x480 4:3 analog_0 restore',
)
sys.path[:0] = [str(pm / 'exlibs'), str(pm / 'pylibs')]
from harbourmaster.platform import HM_PLATFORMS
from harbourmaster.platform.arkos import PlatformdArkOS

class QEMUPlatform(PlatformdArkOS):
    MOVE_PM_BASH = False
    ES_NAME = 'show-refresh'

    def __init__(self, hm):
        # Do not move/delete our Ports menu launcher as the board adapter does.
        from harbourmaster.platform.base import PlatformBase
        PlatformBase.__init__(self, hm)

HM_PLATFORMS['darkos-qemu'] = QEMUPlatform
if '--cli' in sys.argv:
    from harbourmaster.cli import main
    raise SystemExit(main(['harbourmaster', '--no-check', *sys.argv[sys.argv.index('--cli') + 1:]]))
# Use HarbourMaster's installation path for the offline, pinned pilot archive.
pilot = pm / 'autoinstall/sdlpop.zip'
if pilot.is_file():
    from harbourmaster.cli import main
    result = main(['harbourmaster', '--no-check', '--offline', 'install', str(pilot)])
    if result:
        raise SystemExit(result)
    pilot.unlink()
# ctypes resolves SDL functions from an explicit library handle, bypassing the
# preload helper. Read the SDL renderer only during requested test captures.
if os.environ.get('DARKOS_QEMU_CAPTURE') == '1':
    import ctypes
    import sdl2
    import sdl2.render
    present = sdl2.render.SDL_RenderPresent
    def capture_present(renderer):
        request = Path('/run/darkos-qemu/capture.request')
        if request.exists():
            w, h = ctypes.c_int(), ctypes.c_int()
            sdl2.SDL_GetRendererOutputSize(renderer, ctypes.byref(w), ctypes.byref(h))
            if 0 < w.value <= 8192 and 0 < h.value <= 8192:
                pixels = ctypes.create_string_buffer(w.value * h.value * 3)
                sdl2.SDL_RenderFlush(renderer)
                if sdl2.SDL_RenderReadPixels(renderer, None, sdl2.SDL_PIXELFORMAT_RGB24,
                                             pixels, w.value * 3) == 0:
                    target = request.with_name('frame.ppm')
                    tmp = target.with_suffix('.partial')
                    tmp.write_bytes(f'P6\n{w.value} {h.value}\n255\n'.encode() + pixels.raw)
                    tmp.replace(target)
                    request.unlink()
        present(renderer)
    sdl2.render.SDL_RenderPresent = capture_present
# Keep the pinned version until an explicit user update; catalogue remains online.
bootstrap = runpy.run_path(str(pm / 'pugwash'), run_name='darkos_qemu_bootstrap')
import importlib
importlib.import_module('pugwash.main').portmaster_check_update = lambda *args: False
raise SystemExit(bootstrap['main']([str(pm / 'pugwash'), *sys.argv[1:]]))
