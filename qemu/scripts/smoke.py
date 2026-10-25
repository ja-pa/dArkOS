"""One cold boot and the shared Game Boy scenario; never build or attest."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess as sp
import sys
import time

Q = Path(__file__).resolve().parents[1]


def load_vm():
    spec = importlib.util.spec_from_file_location('smoke_vm', Q / 'scripts/workflow-vm.py')
    vm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vm)
    return vm


def prepared(work, env):
    required = [work / 'state/profile.env', work / 'state/profile.json',
                work / 'state/image.json', work / 'state/runtime-id',
                Path(env['DISK_IMAGE']), Path(env['KERNEL_IMAGE']), Path(env['SSH_KEY'])]
    if any(not path.is_file() or not path.stat().st_size for path in required):
        raise RuntimeError('Runtime is not prepared; build with make qemu-image first. Smoke never builds.')
    profile = json.loads((work / 'state/profile.json').read_text())
    if not profile.get('root_partuuid') or not profile.get('root_fstype'):
        raise RuntimeError('Runtime image profile is incomplete; run make qemu-image first')
    return {'runtime_id': (work / 'state/runtime-id').read_text().strip(),
            'image_fingerprint': json.loads((work / 'state/image.json').read_text())['fingerprint']}


def command(args, env, log):
    sp.run(args, env=env, stdin=sp.DEVNULL, stdout=log, stderr=sp.STDOUT, check=True)


def run(work, env):
    identity = prepared(work, env)
    # Use the same lock as the conversion/full-test pipeline, without running it.
    with (work / 'state/pipeline.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another pipeline or smoke test owns WORK_DIR')
        vm = load_vm()
        if vm.identity(False):
            raise RuntimeError('VM is already running; stop it before starting a smoke test')
        output = work / 'logs/smoke'
        output.mkdir(parents=True, exist_ok=True)
        env = dict(env, QEMU_VM_LOG=str(output / 'serial.log'))
        result = {**identity, 'profile': 'smoke', 'passed': False,
                  'clean_shutdown': False, 'disk_checked': False}
        (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
        started = time.monotonic()
        workflow = [sys.executable, str(Q / 'scripts/workflow-vm.py')]
        with (output / 'smoke.log').open('w') as log:
            try:
                # The lifecycle lock rechecks stopped state atomically with start.
                command([*workflow, 'start', 'gtk-gl', '--require-stopped'], env, log)
                owned_pid = vm.identity()[0]
                command(['bash', str(Q / 'scripts/graphics-ssh.sh'),
                         'test -e /dev/dri/card0 && findmnt /roms && '
                         'nmcli -g GENERAL.CONNECTION device show enp0s2 | grep -Fx "QEMU VirtIO Ethernet"'], env, log)
                command([sys.executable, str(Q / 'tests/integration.py'), '--profile', 'smoke'], env, log)
                if vm.identity()[0] != owned_pid:
                    raise RuntimeError('VM identity changed; leaving it running for diagnosis')
                command([*workflow, 'stop'], env, log)
                result['clean_shutdown'] = True
                command([*workflow, 'check'], env, log)
                result['disk_checked'] = True
                result['passed'] = True
            except Exception as error:
                result['error'] = str(error)
                raise
            finally:
                result['duration_seconds'] = round(time.monotonic() - started, 3)
                (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
                print(f'Smoke diagnostics: {output}', flush=True)
        print(f"Smoke passed in {result['duration_seconds']:.1f}s (not full release validation)")
        return result


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    run(Path(os.environ['WORK_DIR']), dict(os.environ))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, sp.CalledProcessError) as error:
        sys.exit(f'Error: {error}')
