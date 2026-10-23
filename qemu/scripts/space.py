"""Check native and Windows backing storage before allocating artifacts."""
from pathlib import Path
import shutil
import sys

def require_space(path, required):
    path = Path(path).resolve()
    while not path.exists():
        path = path.parent
    paths = [path]
    if Path('/proc/sys/fs/binfmt_misc/WSLInterop').exists() and Path('/mnt/c').is_dir():
        paths.append(Path('/mnt/c'))
    for target in paths:
        free = shutil.disk_usage(target).free
        if free < required:
            raise ValueError(f'Insufficient space on {target}: {free / 2**30:.1f} GiB free; need {required / 2**30:.1f} GiB. Existing data was preserved.')

if __name__ == '__main__':
    try:
        require_space(sys.argv[1], int(sys.argv[2]))
    except ValueError as error:
        sys.exit(str(error))
