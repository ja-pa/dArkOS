"""Shared bundle checksums and path validation, retained from darkos_qemu."""
import hashlib,json
from pathlib import Path
def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def seal(directory, kind):
    files = {}
    for path in sorted(directory.rglob('*')):
        if path != directory / 'bundle.json' and path.is_file() and not path.is_symlink():
            files[str(path.relative_to(directory))] = checksum(path)
    (directory / 'bundle.json').write_text(json.dumps({'format': 1, 'kind': kind, 'files': files}, indent=2) + '\n')

def verify(directory, kind):
    data = json.loads((directory / 'bundle.json').read_text())
    if data['format'] != 1 or data['kind'] != kind:
        raise ValueError('Unexpected bundle format/type')
    for name, expected in data['files'].items():
        path = directory / name
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()) or checksum(path) != expected:
            raise ValueError(f'Bundle checksum/path failure: {name}')
    if kind == 'runtime':
        for name in ['runtime.qcow2', 'Image', 'runtime-id', 'provenance.json', 'LICENSES.txt']:
            if name not in data['files']:
                raise ValueError(f'Missing bundle member: {name}')
    return data
