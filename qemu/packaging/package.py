"""Export a prepared G350 runtime as a standalone user release (no SDK)."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess as sp
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'qemu/scripts'))
from release_config import selection
UNKNOWN = "unavailable"


def run(*args, **kwargs):
    return sp.check_output(list(map(str, args)), text=True, **kwargs).strip()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def code_identity(repo=REPO):
    commit = run('git', '-C', repo, 'rev-parse', 'HEAD')
    diff = sp.check_output(['git', '-C', str(repo), 'diff', '--binary', 'HEAD', '--'])
    untracked = sp.check_output(['git', '-C', str(repo), 'ls-files', '--others', '--exclude-standard', '-z'])
    index = sp.check_output(['git', '-C', str(repo), 'diff', '--cached', '--binary', 'HEAD', '--'])
    digest = hashlib.sha256(diff + b'\0INDEX\0' + index)
    for raw in sorted(filter(None, untracked.split(b'\0'))):
        path = repo / os.fsdecode(raw)
        digest.update(raw + b'\0')
        digest.update(os.readlink(path).encode() if path.is_symlink() else path.read_bytes())
        digest.update(str(path.lstat().st_mode).encode())
    dirty = bool(diff or index or untracked)
    suffix = '-dirty-' + digest.hexdigest()[:12] if dirty else ''
    return {'commit': commit, 'branch': run('git', '-C', repo, 'branch', '--show-current'),
            'dirty': dirty, 'changes_sha256': digest.hexdigest() if dirty else None,
            'id': 'g' + commit[:12] + suffix}


def release_name(image, code):
    base = re.sub(r'^darkos_', '', image, flags=re.I)
    base = re.sub(r'\.img$', '', base, flags=re.I)
    base = re.sub(r'[^a-z0-9.-]+', '-', base.lower()).strip('-.')
    if not base:
        raise ValueError('Missing original image version')
    return 'darkos-qemu-' + base + '-' + code['id']


def validate_release(selected, resolved):
    if selected['input'] != resolved['input']:
        raise ValueError('RELEASE_LOCK differs from the prepared runtime state/resolved-release.json')
    if resolved['input'].get('source_board') != 'g350':
        raise ValueError('Only the prepared G350 QEMU runtime is supported')


def package(stage, profile):
    shutil.copytree(REPO / 'qemu/packaging/templates', stage, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (stage / 'config').mkdir()
    shutil.copy2(REPO / 'qemu/config/controls.json', stage / 'config/controls.json')
    (stage / 'assets').mkdir()
    shutil.copy2(REPO / 'qemu/assets/controls-template.png', stage / 'assets/controls-template.png')
    for name in ('controls-window.py', 'qemu-audio.sh'):
        shutil.copy2(REPO / 'qemu/scripts' / name, stage / 'scripts' / name)
    shutil.copy2(REPO / 'qemu/tests/fixtures/test-roms-LICENSES.md', stage / 'G350-ROM-NOTICES.md')
    shutil.copy2(REPO / 'qemu/docs/PORTMASTER.md', stage / 'PORTMASTER.md')
    shutil.copy2(REPO / 'qemu/docs/PICO8.md', stage / 'PICO8.md')
    write(stage / 'config/image.json', {**profile, 'guest_layout': 'g350', 'memory_mb': 2048})
    for path in stage.rglob('*.sh'):
        path.chmod(0o755)


def seal(stage):
    files = sorted(p for p in stage.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (stage / 'SHA256SUMS').write_text(''.join(
        f'{sha(path)}  {path.relative_to(stage).as_posix()}\n' for path in files))
    sp.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=stage, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=REPO / 'dist/qemu')
    parser.add_argument('--dry-run', action='store_true', help='show identity and paths without exporting')
    args = parser.parse_args(argv)
    selected = selection()
    work = Path(selected['WORK_DIR'])
    disk = Path(os.environ.get('DISK_IMAGE', work / 'images/work.qcow2')).resolve()
    kernel = Path(os.environ.get('KERNEL_IMAGE', work / 'build/arch/arm64/boot/Image')).resolve()
    lock = Path(selected['RELEASE_LOCK'])
    resolved = read(work / 'state/resolved-release.json')
    validate_release(read(lock), resolved)
    profile = read(work / 'state/profile.json')
    code = code_identity()
    name = release_name(resolved['input']['image_filename'], code)
    target = args.output_root.resolve() / name
    stage = target.with_name(target.name + '.partial')
    if target.exists() or stage.exists():
        raise ValueError(f'Refusing to overwrite existing release or partial: {target}')
    if args.dry_run:
        print(json.dumps({'release_id': name, 'output': str(target), 'disk': str(disk),
                          'kernel': str(kernel), 'code': code}, indent=2))
        return
    for command in ('qemu-img', 'qemu-nbd', 'sha256sum', 'unshare', 'mount', 'flock'):
        if not shutil.which(command):
            raise ValueError(f'Missing dependency: {command}')
    env = dict(os.environ, WORK_DIR=str(work), DISK_IMAGE=str(disk),
               KERNEL_IMAGE=str(kernel), RELEASE_LOCK=str(lock))
    sp.run(['bash', str(REPO / 'qemu/vm.sh'), 'check'], env=env, check=True)
    info = json.loads(run('qemu-img', 'info', '--output=json', disk))
    required = info['virtual-size'] + kernel.stat().st_size + 1024**3
    ancestor = target.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    if shutil.disk_usage(ancestor).free < required:
        raise ValueError(f'Export requires at least {required // 1024**3 + 1} GiB free temporary space')
    # A WSL virtual filesystem can advertise more space than its Windows host.
    if Path('/proc/sys/fs/binfmt_misc/WSLInterop').exists() and Path('/mnt/c').is_dir():
        if shutil.disk_usage('/mnt/c').free < required:
            raise ValueError('Insufficient free space on the Windows backing drive C:')
    build = read(work / 'artifacts/delta.json')
    kernel_source = read(work / 'artifacts/kernel-source.json')
    kernel_sha = sha(kernel)
    if kernel_source.get('image_sha256') != kernel_sha:
        raise ValueError('Kernel differs from artifacts/kernel-source.json; attest it before exporting')
    upgrade_path = work / 'artifacts/audio-upgrade.json'
    upgrade = read(upgrade_path) if upgrade_path.exists() else None
    if upgrade and upgrade.get('new_kernel_sha256') != kernel_sha:
        raise ValueError('Kernel differs from recorded audio upgrade')
    target.parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()
    print(f'Exporting to {stage}', flush=True)
    try:
        package(stage, profile)
        output = stage / 'darkos.qcow2'
        sp.run(['qemu-img', 'convert', '-p', '-c', '-O', 'qcow2', str(disk), str(output)], check=True)
        root_command = ['bash', str(REPO / 'qemu/scripts/with-disk.sh'), str(output), 'rw',
                        'bash', str(REPO / 'qemu/packaging/guest/prepare-guest.sh')]
        if os.geteuid() != 0:
            root_command = ['sudo', '--', 'env', f'WORK_DIR={work}', f'RELEASE_LOCK={lock}', *root_command]
        sp.run(root_command, env=env, check=True)
        standalone = json.loads(run('qemu-img', 'info', '--output=json', output))
        if standalone['format'] != 'qcow2' or 'backing-filename' in standalone:
            raise ValueError('Export is not standalone QCOW2')
        sp.run(['qemu-img', 'check', str(output)], check=True)
        shutil.copy2(kernel, stage / 'Image')
        recipes = {str(p.relative_to(REPO)): sha(p) for p in sorted((REPO / 'qemu').rglob('*'))
                   if p.is_file() and '__pycache__' not in p.parts}
        recipes['make_qemu_release.sh'] = sha(REPO / 'make_qemu_release.sh')
        provenance = {'schema': 1, 'release_id': name,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'source': {'image': resolved['input'], 'component_sources': resolved.get('sources', UNKNOWN)},
            'packaging': code, 'recipe_sha256': recipes,
            'runtime_build': {k: v for k, v in build.items() if k not in ('changes', 'package_installation', 'validation')},
            'kernel': {**{k: v for k, v in kernel_source.items() if k != 'transport_repo'}, 'sha256': kernel_sha},
            'audio_upgrade': upgrade if upgrade else UNKNOWN,
            'runtime_id': (work / 'state/runtime-id').read_text().strip(),
            'disk': {'format': 'qcow2', 'backing_file': None, 'writable': True}}
        for key in ('image_sha256', 'upstream_release', 'archives'):
            provenance['source']['image'].setdefault(key, UNKNOWN)
        provenance['portmaster'] = build.get('portmaster', {'status': 'not installed in this runtime'})
        write(stage / 'provenance.json', provenance)
        if code_identity() != code:
            raise ValueError('Packaging checkout changed during export; retry from a stable checkout')
        seal(stage)
        # Refuse a competing publisher; the parent is controlled by this user.
        if target.exists():
            raise ValueError(f'Target appeared during export: {target}')
        stage.rename(target)
    except BaseException:
        print(f'Export incomplete; retained for inspection: {stage}', file=sys.stderr)
        raise
    print(f'Release ready: {target}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, sp.CalledProcessError) as error:
        sys.exit(f'Release: {error}')
