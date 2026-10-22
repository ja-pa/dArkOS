"""Pinned PortMaster download, portable pilot package, and offline installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import urllib.request
import zipfile

Q = Path(__file__).resolve().parents[1]

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def extract(archive, dest):
    # Upstream archives are pinned, but never permit writes outside the target.
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            path = Path(entry.filename)
            if path.is_absolute() or '..' in path.parts or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('Unsafe archive entry: ' + entry.filename)
        z.extractall(dest)
        for entry in z.infolist():
            path = dest / entry.filename
            if path.is_file():
                path.chmod(0o755 if entry.external_attr >> 16 & 0o111 else 0o644)

def prepare(work):
    lock = json.loads((Q/'locks/portmaster.lock.json').read_text())
    out = work / 'artifacts/portmaster'
    out.mkdir(parents=True, exist_ok=True)
    for key, name in [('portmaster', 'PortMaster.zip'), ('sdlpop', 'sdlpop.zip')]:
        target = out / name
        if not target.exists():
            partial = target.with_suffix('.partial')
            urllib.request.urlretrieve(lock[key]['url'], partial)
            if sha(partial) != lock[key]['sha256']:
                raise ValueError('Download checksum mismatch: ' + name)
            partial.replace(target)
        if sha(target) != lock[key]['sha256']:
            raise ValueError('Cached checksum mismatch: ' + name)
    (out / 'portable').mkdir(exist_ok=True)
    portable = out / 'portable/sdlpop.zip'
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        tree = Path(tmp)
        extract(out / 'sdlpop.zip', tree)
        shutil.copy2(tree / 'SDLPoP.sh', tree / 'sdlpop/launch-handheld.txt')
        shutil.copy2(Q / 'ports/SDLPoP.sh', tree / 'SDLPoP.sh')
        (tree / 'SDLPoP.sh').chmod(0o755)
        with zipfile.ZipFile(portable, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(tree.rglob('*')):
                if not path.is_file():
                    continue
                info = zipfile.ZipInfo(path.relative_to(tree).as_posix(), (2026, 1, 1, 0, 0, 0))
                info.external_attr = (0o100755 if path.stat().st_mode & 0o111 else 0o100644) << 16
                z.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(portable) as z:
        binary_sha256 = hashlib.sha256(z.read('sdlpop/prince.aarch64')).hexdigest()
    data = {'schema': 1, 'sources': lock,
            'portable_zip': {'name': 'portable/sdlpop.zip', 'sha256': sha(portable)},
            'launcher_sha256': sha(Q / 'ports/SDLPoP.sh'),
            'game_binary': 'Unmodified upstream prince.aarch64 shared by QEMU and G350',
            'game_binary_sha256': binary_sha256,
            'hardware_validation': 'Not yet tested on physical G350'}
    (out / 'manifest.json').write_text(json.dumps(data, indent=2) + '\n')
    (out / 'SHA256SUMS').write_text(''.join(f'{sha(out / n)}  {n}\n' for n in
        ['PortMaster.zip', 'sdlpop.zip', 'portable/sdlpop.zip', 'manifest.json']))
    return out

def install(work, root):
    out = work / 'artifacts/portmaster'
    for line in (out / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if sha(out / name) != expected:
            raise ValueError('Prepared package checksum mismatch: ' + name)
    pm = root / 'opt/tools/PortMaster'
    manifest = root / 'opt/darkos-qemu/portmaster-manifest.json'
    # Repackaging must preserve user-installed ports and an explicitly updated PM.
    if not pm.exists():
        extract(out / 'PortMaster.zip', root / 'opt/tools')
    elif not manifest.is_file():
        raise ValueError('Unmanaged PortMaster exists; refusing to overwrite it')
    elif json.loads(manifest.read_text())['sources']['portmaster'] != json.loads((out / 'manifest.json').read_text())['sources']['portmaster']:
        raise ValueError('Installed PortMaster pin differs; use a fresh runtime for this version')
    ports = root / 'roms/ports'
    ports.mkdir(parents=True, exist_ok=True)
    (ports / 'PortMaster.sh').write_text('#!/usr/bin/env bash\nexec bash /opt/darkos-qemu/ports.sh /roms/ports/PortMaster.sh\n')
    (ports / 'PortMaster.sh').chmod(0o755)
    autoinstall = pm / 'autoinstall'
    autoinstall.mkdir(exist_ok=True)
    # Let HarbourMaster perform the actual installation, including metadata.
    if not (ports / 'sdlpop/prince.aarch64').is_file():
        shutil.copy2(out / 'portable/sdlpop.zip', autoinstall / 'sdlpop.zip')
    manifest.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads((out / 'manifest.json').read_text())
    data['installed'] = {'version': (pm / 'version').read_text().strip(),
        'files': {name: sha(pm / name) for name in ['pugwash', 'control.txt', 'device_info.txt']}}
    manifest.write_text(json.dumps(data, indent=2) + '\n')
    print('PortMaster installed; pilot ZIP queued for PortMaster autoinstall')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'install'])
    args = parser.parse_args()
    work = Path(os.environ['WORK_DIR'])
    if args.action == 'prepare':
        print(prepare(work))
    else:
        install(work, Path(os.environ['ROOT']))

if __name__ == '__main__':
    main()
