"""Shared release selection for shell tools, diagnostics and packaging."""
import json
import os
from pathlib import Path
import shlex

Q = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = Q / 'locks/g350-v08272026.json'
DEFAULT_WORK = Path.home() / 'darkos-g350-qemu-v08272026'

def selection(env=None):
    env = os.environ if env is None else env
    lock = Path(env.get('RELEASE_LOCK', DEFAULT_LOCK)).resolve()
    work = Path(env.get('WORK_DIR', DEFAULT_WORK)).resolve()
    data = json.loads(lock.read_text())
    image = data['input']['image_filename']
    if Path(image).name != image or not image.endswith('.img'):
        raise ValueError('Release image filename must be a plain .img filename')
    return {'WORK_DIR': str(work), 'RELEASE_LOCK': str(lock),
            'RAW_IMAGE': str(Path(env.get('RAW_IMAGE', work / 'images' / image)).resolve())}

if __name__ == '__main__':
    for key, value in selection().items():
        print('export ' + key + '=' + shlex.quote(value))
