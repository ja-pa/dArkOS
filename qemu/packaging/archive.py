"""Create split GitHub release assets without modifying the exported payload."""
import argparse
from contextlib import ExitStack, contextmanager
import fcntl
import gzip
import hashlib
import json
import io
import os
import shutil
from pathlib import Path
import re
import subprocess as sp
import sys
import tarfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'qemu/scripts'))
from space import require_space

LIMIT = 2 * 1024**3  # GitHub assets must be strictly smaller than 2 GiB.
REQUIRED = {
    'darkos.qcow2', 'Image', 'SHA256SUMS', 'provenance.json', 'README.md',
    'LICENSES.txt', 'G350-ROM-NOTICES.md', 'PORTMASTER.md', 'start.sh', 'stop.sh',
    'controls.sh', 'assets/controls-template.png', 'config/image.json',
    'config/controls.json', 'scripts/release-vm.py', 'scripts/controls-window.py',
    'scripts/common.sh', 'scripts/run-qemu.sh', 'scripts/qemu-audio.sh',
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(source):
    # Do not trust arbitrary paths in an edited checksum file or follow symlinks.
    for name in REQUIRED:
        path = source / name
        for parent in (path, *path.parents):
            if parent == source:
                break
            if parent.is_symlink():
                raise ValueError(f'Symlink in release payload: {name}')
        if not path.is_file():
            raise ValueError(f'Missing release file: {name}')
    manifest = {}
    for line in (source / 'SHA256SUMS').read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match:
            raise ValueError('Invalid SHA256SUMS line')
        digest, name = match.groups()
        if name not in REQUIRED - {'SHA256SUMS'} or name in manifest:
            raise ValueError(f'Unexpected or duplicate manifest path: {name}')
        manifest[name] = digest
    if set(manifest) != REQUIRED - {'SHA256SUMS'}:
        raise ValueError('SHA256SUMS does not describe the complete release')
    return manifest


def verify(source, manifest):
    for name, digest in manifest.items():
        if sha(source / name) != digest:
            raise ValueError(f'Release file changed: {name}. Use the untouched export; test a copy. '
                             'For a tested disk use --clean-tested-disk; do not reseal a used disk.')


@contextmanager
def stopped(source):
    # Same locks as release-vm.py; prevent a start racing with the archive read.
    state = source / '.runtime/state'
    state.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        for name in ('action.lock', 'vm.lock'):
            lock = stack.enter_context((state / name).open('a'))
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Release VM is running or start/stop is in progress; use stop.sh first')
        yield


class SplitWriter:
    def __init__(self, folder, name, size):
        self.folder, self.name, self.size = folder, name, size
        self.stream = None
        self.used = 0
        self.parts = []

    def write(self, data):
        view = memoryview(data)
        length = len(view)
        while view:
            if self.stream is None or self.used == self.size:
                self.close()
                if len(self.parts) >= 998:
                    raise ValueError('Too many parts for a GitHub release (maximum 1000 assets)')
                path = self.folder / f'{self.name}.tar.gz.{len(self.parts) + 1:03d}'
                self.stream = path.open('xb')
                self.parts.append(path)
                self.used = 0
            count = min(len(view), self.size - self.used)
            self.stream.write(view[:count])
            self.used += count
            view = view[count:]
        return length

    def flush(self):
        if self.stream:
            self.stream.flush()

    def close(self):
        if self.stream:
            self.stream.close()
            self.stream = None


def archive(source, folder, name, size):
    writer = SplitWriter(folder, name, size)
    try:
        # Stream compressed data directly into parts; no second multi-GB tar file.
        with gzip.GzipFile(filename='', mode='wb', fileobj=writer, mtime=0, compresslevel=1) as zipped:
            with tarfile.open(fileobj=zipped, mode='w|', format=tarfile.PAX_FORMAT) as tar:
                for item in sorted(REQUIRED):
                    path = source / item
                    info = tar.gettarinfo(str(path), arcname=f'{name}/{item}')
                    if not info.isfile():
                        raise ValueError(f'Release payload is no longer a regular file: {item}')
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ''
                    info.pax_headers = {}
                    info.mode = 0o755 if item.endswith('.sh') else 0o644
                    with path.open('rb') as stream:
                        tar.addfile(info, stream)
    finally:
        writer.close()
    return writer.parts


def clean_payload(source, partial, name, provenance, original):
    payload = partial / 'payload'
    payload.mkdir()
    for item in REQUIRED - {'darkos.qcow2'}:
        target = payload / item
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / item, target)
    disk = payload / 'darkos.qcow2'
    # The source has already passed standalone/locking checks; retain its bytes.
    shutil.copy2(source / 'darkos.qcow2', disk)
    work = partial / 'mount-work'
    cleanup = REPO / 'qemu/packaging/guest/clean-tested-guest.sh'
    command = ['env', f'WORK_DIR={work}', 'bash', str(REPO / 'qemu/scripts/with-disk.sh'),
               str(disk), 'rw', 'bash', str(cleanup)]
    if os.geteuid() != 0:
        command = ['sudo', '-n', '--', *command]
    sp.run(command, check=True)
    # Remove root-owned mount bookkeeping while the sudo timestamp is fresh.
    command = ['rm', '-r', '--', str(work)]
    if os.geteuid() != 0:
        command = ['sudo', '-n', '--', *command]
    sp.run(command, check=True)
    sp.run(['qemu-img', 'check', str(disk)], check=True)
    provenance = {**provenance, 'release_id': name,
                  'distribution_cleanup': {'source_disk_sha256': original['darkos.qcow2'],
                                           'script_sha256': sha(cleanup),
                                           'sanitizer_sha256': sha(REPO / 'qemu/scripts/sanitize.sh'),
                                           'removed': ['guest logs', 'SSH identity and keys',
                                                       'RetroArch saves/states', 'ROM saves/states'],
                                           'preserved': ['installed games', 'configuration']}}
    (payload / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    manifest = {item: sha(payload / item) for item in REQUIRED - {'SHA256SUMS'}}
    (payload / 'SHA256SUMS').write_text(''.join(
        f'{digest}  {item}\n' for item, digest in sorted(manifest.items())))
    return payload, manifest


class JoinedReader(io.RawIOBase):
    def __init__(self, parts):
        super().__init__()
        self.parts = iter(parts)
        self.stream = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.stream is None:
                path = next(self.parts, None)
                if path is None:
                    return 0
                self.stream = path.open('rb')
            count = self.stream.readinto(buffer)
            if count:
                return count
            self.stream.close()
            self.stream = None

    def close(self):
        if self.stream:
            self.stream.close()
        super().close()


def verify_archive(parts, name, expected):
    seen = set()
    with JoinedReader(parts) as raw, io.BufferedReader(raw) as joined:
        with gzip.GzipFile(fileobj=joined, mode='rb') as zipped:
            with tarfile.open(fileobj=zipped, mode='r|') as tar:
                for item in tar:
                    prefix = name + '/'
                    relative = item.name[len(prefix):] if item.name.startswith(prefix) else ''
                    if not item.isfile() or relative not in expected or relative in seen:
                        raise ValueError(f'Unexpected archive entry: {item.name}')
                    digest = hashlib.sha256()
                    with tar.extractfile(item) as stream:
                        while chunk := stream.read(1024**2):
                            digest.update(chunk)
                    if digest.hexdigest() != expected[relative]:
                        raise ValueError(f'Archived bytes differ: {relative}')
                    seen.add(relative)
            # Consume padding and gzip trailer too, checking CRC/truncation.
            while zipped.read(1024**2):
                pass
    if seen != set(expected):
        raise ValueError('Incomplete archive')


def write_upload(folder, name, commit, parts):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid packaging commit in provenance.json')
    assets = ' '.join(path.name for path in parts)
    script = folder / 'upload-draft.sh'
    script.write_text(f'''#!/usr/bin/env bash
# Upload only after local validation. Publishing remains a separate GitHub action.
set -euo pipefail
[[ $# == 1 && -n $1 ]] || {{ echo "Usage: $0 NEW_TAG" >&2; exit 2; }}
cd -- "$(dirname -- "$0")"
command -v gh >/dev/null || {{ echo 'Install GitHub CLI and run gh auth login first' >&2; exit 1; }}
sha256sum -c SHA256SUMS
exec gh release create "$1" --repo ja-pa/dArkOS --draft \\
  --target {commit} --title "{name}" --notes-file RELEASE.md \\
  {assets} SHA256SUMS RELEASE.md
''')
    script.chmod(0o755)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release', type=Path, help='standalone export; test a copy or use --clean-tested-disk')
    parser.add_argument('--output-root', type=Path, default=REPO / 'dist/qemu/github')
    parser.add_argument('--part-size-mib', type=int, default=1900)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--clean-tested-disk', action='store_true',
                        help='copy a tested disk and remove guest logs, keys and test saves (requires sudo)')
    args = parser.parse_args(argv)
    size = args.part_size_mib * 1024**2
    if not 0 < size < LIMIT:
        raise ValueError('Part size must be between 1 and 2047 MiB')
    source = args.release.resolve(strict=True)
    provenance = json.loads((source / 'provenance.json').read_text())
    name = provenance['release_id']
    if not re.fullmatch(r'darkos-qemu-[a-z0-9.-]+', name):
        raise ValueError('Unsafe release_id in provenance.json')
    if not re.fullmatch(r'[0-9a-f]{40}', provenance['packaging']['commit']):
        raise ValueError('Invalid packaging commit in provenance.json')
    if provenance['packaging']['dirty']:
        raise ValueError('Public assets require an export from a clean committed checkout')
    if args.clean_tested_disk:
        name += '-cleaned'
    target = args.output_root.resolve() / name
    partial = target.with_name(name + '.partial')
    if target == source or source in target.parents or target in source.parents:
        raise ValueError('Output must be outside the source release')
    if target.exists() or partial.exists():
        raise ValueError(f'Refusing to overwrite assets or partial output: {target}')
    manifest = inventory(source)
    required = sum((source / item).stat().st_size for item in REQUIRED) + 256 * 1024**2
    if args.clean_tested_disk:
        # A cleaned QCOW2 can expand while new Btrfs metadata is written.
        virtual = json.loads(sp.check_output(['qemu-img', 'info', '--output=json', str(source / 'darkos.qcow2')]))['virtual-size']
        required = 2 * virtual + 256 * 1024**2
    details = {'release_id': name, 'source': str(source), 'output': str(target),
               'part_size_bytes': size, 'required_free_bytes': required,
               'included': sorted(REQUIRED), 'excluded': 'all other files, including .runtime and logs'}
    if args.dry_run:
        print(json.dumps(details, indent=2))
        return
    if args.clean_tested_disk and os.geteuid() != 0:
        result = sp.run(['sudo', '-n', 'true'], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        if result.returncode:
            raise ValueError('Cleaning needs root: run sudo -v in this terminal, then retry; no copy was created')
    require_space(target.parent, required)
    with stopped(source):
        print('Verifying original release checksums and disk...', flush=True)
        verify(source, {k: v for k, v in manifest.items() if not (args.clean_tested_disk and k == 'darkos.qcow2')})
        original = {**manifest, 'darkos.qcow2': sha(source / 'darkos.qcow2')} if args.clean_tested_disk else manifest
        info = json.loads(sp.check_output(['qemu-img', 'info', '--output=json', str(source / 'darkos.qcow2')]))
        if info['format'] != 'qcow2' or 'backing-filename' in info:
            raise ValueError('Release disk must be standalone QCOW2')
        sp.run(['qemu-img', 'check', str(source / 'darkos.qcow2')], check=True)
        partial.mkdir(parents=True)
        try:
            print(f'Archiving into {partial}', flush=True)
            payload, payload_manifest = source, manifest
            if args.clean_tested_disk:
                payload, payload_manifest = clean_payload(source, partial, name, provenance, original)
            parts = archive(payload, partial, name, size)
            print('Verifying joined archive contents...', flush=True)
            verify_archive(parts, name, {**payload_manifest, 'SHA256SUMS': sha(payload / 'SHA256SUMS')})
            # Check again so an external edit cannot produce a successfully sealed archive.
            if inventory(source) != manifest:
                raise ValueError('Release manifest changed while archiving')
            verify(source, original)
            (partial / 'SHA256SUMS').write_text(''.join(
                f'{sha(path)}  {path.name}\n' for path in parts))
            instructions = f"""# {name}

Download every `.tar.gz.001`, `.002`, etc. part and `SHA256SUMS` into one folder.
On Linux or Ubuntu WSL, verify and extract:

```bash
sha256sum -c SHA256SUMS
cat {name}.tar.gz.[0-9][0-9][0-9] | tar -xz
cd {name}
sha256sum -c SHA256SUMS
bash start.sh
```

On Windows, use the native Linux filesystem inside WSL. The package requires
a Linux graphical session (WSLg on Windows); see the included README.md for
dependencies, keyboard controls and clean shutdown.
Each part is at most {args.part_size_mib} MiB, below the 2 GiB asset limit.
The archive contains only verified export payloads, without host logs or .runtime
state. Tested-disk cleanup mode: {args.clean_tested_disk}.
The included provenance.json describes source identity and available hashes.
Export revision: `{provenance['packaging']['commit']}`.

Extract a separate copy for testing. Booting changes the disk and its checksum.

"""
            (partial / 'RELEASE.md').write_text(instructions)
            write_upload(partial, name, provenance['packaging']['commit'], parts)
            sp.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=partial, check=True)
            if target.exists():
                raise ValueError(f'Output appeared during archive creation: {target}')
            if args.clean_tested_disk:
                shutil.rmtree(payload)
            partial.rename(target)
        except BaseException:
            print(f'Incomplete assets retained for inspection: {partial}', file=sys.stderr)
            raise
    print(f'GitHub assets ready: {target}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, EOFError, tarfile.TarError, sp.CalledProcessError) as error:
        sys.exit(f'Archive: {error}')
