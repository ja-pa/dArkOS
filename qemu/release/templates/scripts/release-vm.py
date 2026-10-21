"""Standalone Linux release lifecycle; no SSH, SDK or development environment."""
import argparse
import fcntl
import json
import os
import re
from pathlib import Path
import shutil
import socket
import subprocess as sp
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.runtime'
STATE = WORK / 'state/vm.json'
LOG = WORK / 'logs/qemu.log'
DISK = ROOT / 'darkos.qcow2'


def process_start(pid):
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]


def identity():
    try:
        saved = json.loads(STATE.read_text())
        pid = saved['pid']
        args = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
        expected = f'file={DISK},format=qcow2,if=none,id=hd0'.encode()
        qmp = f'unix:{saved["qmp"]},server=on,wait=off'.encode()
        if (process_start(pid) == saved['started'] and expected in args and qmp in args
                and Path(os.fsdecode(args[0])).name == 'qemu-system-aarch64'):
            return saved
    except (OSError, ValueError, KeyError, IndexError):
        pass
    return None


def qmp_command(path, command):
    try:
        return _qmp_command(path, command)
    except TimeoutError as error:
        raise RuntimeError('QMP timed out; close other QMP monitor clients and retry. VM left running') from error


def _qmp_command(path, command):
    with socket.socket(socket.AF_UNIX) as sock:
        # Bound the wait: QEMU accepts only one active QMP monitor client.
        sock.settimeout(30)
        sock.connect(path)
        with sock.makefile('rwb', buffering=0) as stream:
            if 'QMP' not in json.loads(stream.readline()):
                raise RuntimeError('Invalid QMP greeting')
            for name in ('qmp_capabilities', command):
                stream.write(json.dumps({'execute': name}).encode() + b'\n')
                while True:
                    line = stream.readline()
                    if not line:
                        raise RuntimeError('QMP disconnected')
                    reply = json.loads(line)
                    if 'error' in reply:
                        raise RuntimeError(f'QMP: {reply["error"]}')
                    if 'return' in reply:
                        break


def controls(action):
    sp.run([sys.executable, str(ROOT / 'scripts/controls-window.py'), action, str(WORK)], check=False)


def environment(qmp):
    env = dict(os.environ)
    for key in ('WORK_DIR', 'BUILD_DIR', 'KERNEL_IMAGE', 'DISK_IMAGE', 'SSH_PORT',
                'ROOT_FLAGS', 'EXTRA_APPEND', 'QMP_SOCKET'):
        env.pop(key, None)
    env['QMP_SOCKET'] = qmp
    return env


def check_display(log_path=Path('/mnt/wslg/weston.log')):
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        raise RuntimeError('No graphical display; run in WSLg or a Linux desktop session')
    try:
        with log_path.open('rb') as stream:
            stream.seek(max(0, log_path.stat().st_size - 2 * 1024**2))
            text = stream.read().decode(errors='replace')
    except OSError:
        return  # An ordinary Linux desktop has no WSLg log.
    states = re.findall(r'RDP backend: use_gfxredir\s*=\s*([01])', text)
    if states and states[-1] == '0' and 'rdp_allocate_shared_memory: Failed to open' in text:
        raise RuntimeError('WSLg graphics redirection failed (COPY MODE/shared memory). '
                           'Close WSL GUI apps and restart Weston; see README.md. VM was not started')


def supervise():
    # The supervisor holds this lock for QEMU's complete lifetime.
    with (WORK / 'state/vm.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('This release image is already running')
        # Private short Unix socket path: release folders can exceed sun_path limits.
        with tempfile.TemporaryDirectory(prefix=f'darkos-{os.getuid()}-') as folder:
            path = str(Path(folder) / 'qmp.sock')
            child = sp.Popen(['bash', str(ROOT / 'scripts/run-qemu.sh'), 'gtk-gl'],
                             env=environment(path), stdin=sp.DEVNULL)
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise RuntimeError(f'QEMU exited {child.returncode}; inspect {LOG}')
                    try:
                        qmp_command(path, 'query-status')
                        break
                    except (OSError, RuntimeError):
                        time.sleep(0.1)
                else:
                    # Do not lose ownership of a VM that was slow to start.
                    print(f'Warning: QMP not ready; inspect {LOG}', flush=True)
                saved = {'pid': child.pid, 'started': process_start(child.pid), 'qmp': path}
                temp = STATE.with_suffix('.tmp')
                temp.write_text(json.dumps(saved))
                temp.replace(STATE)
                child.wait()
            finally:
                if child.poll() is None:
                    # Keep the lifetime lock and socket while it is still alive.
                    child.wait()
                STATE.unlink(missing_ok=True)
                controls('stop')


def start(show_controls):
    if identity():
        raise RuntimeError('This release image is already running; use stop.sh first')
    for tool in ('bash', 'qemu-system-aarch64', 'qemu-img'):
        if not shutil.which(tool):
            raise RuntimeError(f'Missing dependency: {tool}; see README.md')
    check_display()
    if not (ROOT / 'Image').is_file() or not DISK.is_file():
        raise RuntimeError('Missing Image or darkos.qcow2; restore the complete release')
    info = json.loads(sp.check_output(['qemu-img', 'info', '--output=json', str(DISK)]))
    if info['format'] != 'qcow2' or 'backing-filename' in info:
        raise RuntimeError('Release disk must be standalone QCOW2 without a backing image')
    with LOG.open('ab') as output:
        supervisor = sp.Popen([sys.executable, str(Path(__file__).resolve()), '_supervise'],
                              stdin=sp.DEVNULL, stdout=output, stderr=output,
                              start_new_session=True)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if supervisor.poll() is not None:
            raise RuntimeError(f'QEMU failed to start; inspect {LOG}')
        saved = identity()
        if saved:
            qmp_command(saved['qmp'], 'query-status')
            if show_controls:
                controls('start')
            print(f'QEMU started; EmulationStation loads automatically. Log: {LOG}')
            return
        time.sleep(0.1)
    raise RuntimeError(f'Start timed out; VM may still be running. Inspect {LOG}; use stop.sh')


def stop():
    saved = identity()
    if saved is None:
        # Never signal a PID from a stale state file.
        controls('stop')
        print('VM is stopped')
        return
    qmp_command(saved['qmp'], 'system_powerdown')
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        current = identity()
        if current is None:
            controls('stop')
            print('Guest shut down cleanly')
            return
        if current != saved:
            raise RuntimeError('VM identity changed while waiting for shutdown')
        time.sleep(0.2)
    raise RuntimeError(f'Poweroff timed out; VM left running. Inspect {LOG}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop', '_supervise'])
    parser.add_argument('--no-controls', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    (WORK / 'state').mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if args.action == '_supervise':
        supervise()
        return
    with (WORK / 'state/action.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another start/stop operation is in progress')
        if args.action == 'start':
            start(not args.no_controls)
        else:
            stop()


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, sp.CalledProcessError) as error:
        sys.exit(f'Error: {error}')
