"""Release replacement review and verified kernel provenance; no guest execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

Q = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def kernel_source(lock):
    source = lock['sources']['kernel']
    if not re.fullmatch(r'[a-f0-9]{40}', source['commit']):
        raise ValueError('Kernel requires a full lowercase commit SHA')
    if not source['repo'] or any(c in source['repo'] for c in '\r\n'):
        raise ValueError('Invalid kernel repository')
    return source


def record_kernel(lock, checkout, image, output):
    expected = kernel_source(lock)
    git = ['git', '-c', 'safe.directory=' + str(Path(checkout).resolve()), '-C', checkout]
    actual = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip()
    if actual != expected['commit']:
        raise ValueError('Actual kernel checkout does not match release lock')
    if subprocess.check_output(git + ['status', '--porcelain'], text=True).strip():
        raise ValueError('Kernel checkout has local changes')
    transport = subprocess.check_output(git + ['remote', 'get-url', 'origin'], text=True).strip()
    data = dict(expected, actual_commit=actual, transport_repo=transport, image_sha256=digest(image))
    path = Path(output)
    temp = path.with_suffix('.partial')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)


def verified_kernel(receipt, lock, image):
    data = json.loads(Path(receipt).read_text())
    source = kernel_source(lock)
    if (data['actual_commit'] != source['commit'] or data['commit'] != source['commit']
            or data['repo'] != source['repo'] or data['image_sha256'] != digest(image)):
        raise ValueError('Kernel provenance does not match release lock and binary; rebuild kernel')
    return data


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def report(lock, work, previous=None):
    lines = ['# QEMU component replacement review', '',
             'Release: ' + lock['input']['upstream_release'],
             'Image: ' + lock['input']['image_filename'],
             'Image SHA256: ' + lock['input']['image_sha256'], '',
             '| Component | Original version | Target version | Source / commit | Action |',
             '|---|---|---|---|---|']
    inventory = {}
    resolved = work / 'state/resolved-release.json'
    if resolved.exists():
        old = json.loads(resolved.read_text())
        if old['input']['image_sha256'] == lock['input']['image_sha256']:
            path = work / 'logs/inspect/files.json'
            if path.exists():
                inventory = json.loads(path.read_text())
        else:
            lines.insert(6, 'WARNING: WORK_DIR belongs to another image; its inventory is excluded.')
    for name in ('emulationstation', 'retroarch', '351files', 'kernel'):
        replacement = lock['replacements'][name]
        source = lock['sources'][name]
        version = replacement.get('base_version')
        if version and replacement.get('base_image_sha256') != lock['input']['image_sha256']:
            version = None
        actual_hash = inventory.get(replacement.get('base_path'), {}).get('sha256')
        if version and actual_hash and actual_hash != replacement.get('base_sha256'):
            version = None
        row = [name, version or 'UNKNOWN (not established for this image)',
               replacement['target_version'], source['repo'] + ' @ ' + source['commit'], replacement['action']]
        lines.append('| ' + ' | '.join(map(cell, row)) + ' |')
    lines += ['', 'Original binary identities (from matching read-only image inventory):']
    for name, replacement in lock['replacements'].items():
        path = replacement.get('base_path')
        sha = inventory.get(path, {}).get('sha256') if path else None
        lines.append('- ' + name + ': ' + (path or 'hardware boot kernel; path not established')
                     + '; SHA256 ' + (sha or 'UNKNOWN'))
        lines.append('  Version evidence: ' + replacement.get('base_version_evidence', 'not recorded'))
    lines += ['', 'Unknown original versions require review before adopting a new release.',
              'Selected source commits do not establish original binary provenance.',
              'Retained from the image: libretro cores, themes, ROM layout and saves.',
              'Debian graphics/runtime packages are also replaced; exact resolved versions are in',
              'artifacts/graphics/runtime-packages.lock (not pinned before first APT resolution).']
    if previous:
        lines += ['', '## Changes from ' + previous['input']['upstream_release'], '',
                  '| Component | Previous target / commit | New target / commit | Status |',
                  '|---|---|---|---|']
        for name in sorted(set(previous['sources']) | set(lock['sources'])):
            before = previous['sources'].get(name, {})
            after = lock['sources'].get(name, {})
            def identity(value, release):
                version = release.get('replacements', {}).get(name, {}).get('target_version', value.get('version', value.get('tag', 'unknown version')))
                return version + '; ' + value.get('repo', 'absent') + ' @ ' + value.get('commit', 'absent')
            a, b = identity(before, previous), identity(after, lock)
            status = 'CHANGED' if a != b else 'UNCHANGED — review retention on image upgrade'
            lines.append('| ' + ' | '.join(map(cell, [name, a, b, status])) + ' |')
        lines += ['', 'Base image: ' + ('CHANGED' if previous['input']['image_sha256'] != lock['input']['image_sha256'] else 'UNCHANGED')]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, default=Path(os.environ.get('RELEASE_LOCK', Q / 'releases/g350-v01302026.json')))
    parser.add_argument('--work-dir', type=Path, default=Path(os.environ.get('WORK_DIR', Path.home() / 'darkos-g350-qemu')))
    parser.add_argument('--compare-lock', type=Path)
    parser.add_argument('--output', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--kernel-source', action='store_true')
    mode.add_argument('--record-kernel', nargs=3, metavar=('CHECKOUT', 'IMAGE', 'OUTPUT'))
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    if args.kernel_source:
        source = kernel_source(lock)
        print(source['repo'])
        print(source['commit'])
    elif args.record_kernel:
        record_kernel(lock, *args.record_kernel)
    else:
        previous = json.loads(args.compare_lock.read_text()) if args.compare_lock else None
        text = report(lock, args.work_dir, previous)
        if args.output:
            args.output.write_text(text)
        print(text, end='')


if __name__ == '__main__':
    main()
