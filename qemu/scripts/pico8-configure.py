"""Disable only the unsupported Splore shortcut, preserving its bytes."""
from pathlib import Path
import os

def disable_splore(carts):
    carts = Path(carts)
    for path in sorted(carts.rglob('*')):
        if path.is_file() and path.name.lower() in ('zzzsplore.p8', 'zzzsplore.png', 'zzzsplore.p8.png'):
            target = path.with_name(path.name + '.qemu-disabled')
            if target.exists():
                if target.read_bytes() != path.read_bytes():
                    raise RuntimeError('Conflicting disabled Splore shortcut: ' + str(target))
                path.unlink()
            else:
                path.rename(target)

if __name__ == '__main__':
    disable_splore(Path(os.environ['ROOT']) / 'roms/pico-8/carts')
