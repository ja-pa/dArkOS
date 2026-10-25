"""Failure paths that must not depend on a live guest or modify real images."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import socket
import unittest
from unittest.mock import patch, Mock

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'

def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "state").mkdir()
        (self.root / "state/profile.env").write_text("export ROOT_PARTUUID=test-02\nexport ROOT_FSTYPE=btrfs\n")
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        self.env = patch.dict(os.environ, {'WORK_DIR': str(self.root), 'DISK_IMAGE': str(self.root / 'work.qcow2'),
                                         'KERNEL_IMAGE': str(self.root / 'Image'), 'SSH_PORT': str(port),
                                         'ES_SYSROOT': str(self.root / 'sdk/sysroot'),
                                         'QMP_SOCKET': str(self.root / 'state/qmp.sock'),
                                         'SSH_HOST': '127.0.0.1'})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_stopped_vm(self):
        vm = load('workflow-vm')
        with patch.object(vm, 'processes', return_value=[]):
            self.assertIsNone(vm.identity(False))
            with self.assertRaisesRegex(RuntimeError, 'stopped'):
                vm.identity()

    def test_foreign_disk_or_port(self):
        vm = load('workflow-vm')
        for same_disk, same_port in [(False, True), (True, False)]:
            with patch.object(vm, 'processes', return_value=[(42, same_disk, same_port, [])]):
                with self.assertRaisesRegex(RuntimeError, 'another VM'):
                    vm.identity(False)

    def test_duplicate_vm(self):
        vm = load('workflow-vm')
        with patch.object(vm, 'processes', return_value=[(1, True, True, []), (2, True, True, [])]):
            with self.assertRaises(RuntimeError):
                vm.identity()

    def test_existing_vm(self):
        vm = load('workflow-vm')
        with patch.object(vm, 'processes', return_value=[(42, True, True, [])]):
            self.assertEqual(vm.identity()[0], 42)

    def test_start_waits_for_preflight_before_looking_for_qemu(self):
        vm = load('workflow-vm')
        process = Mock(pid=42)
        process.poll.return_value = None
        with patch.object(vm, 'identity', side_effect=[None, None, (42, True, True, [])]) as identity, \
                patch.object(vm.time, 'sleep'):
            self.assertEqual(vm.wait_launch(process, 0), 42)
            self.assertEqual(identity.call_args_list, [unittest.mock.call(False)] * 3)

    def test_preflight_failure_shows_only_this_attempt_log(self):
        vm = load('workflow-vm')
        vm.LOG.parent.mkdir(parents=True)
        previous = b'old unrelated failure\n'
        vm.LOG.write_bytes(previous + b'Error: PulseAudio playback did not complete; use QEMU_AUDIO=none\n')
        process = Mock(pid=42)
        process.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, 'PulseAudio playback did not complete') as error:
            vm.wait_launch(process, len(previous))
        self.assertNotIn('old unrelated failure', str(error.exception))
        self.assertNotIn('VM is stopped', str(error.exception))

    def test_preflight_timeout_never_uses_stopped_vm_error(self):
        vm = load('workflow-vm')
        process = Mock(pid=42)
        process.poll.return_value = None
        with patch.object(vm.time, 'monotonic', side_effect=[0, 31]):
            with self.assertRaisesRegex(RuntimeError, 'launcher timed out'):
                vm.wait_launch(process, 0)

    def test_start_requires_restart_to_change_audio(self):
        vm = load('workflow-vm')
        running = (42, True, True, ['qemu-system-aarch64', 'virtio-gpu-gl-pci'])
        with patch.object(vm, 'identity', return_value=running), \
                patch.object(vm, 'wait_ssh') as wait, \
                patch.dict(os.environ, {'QEMU_AUDIO': 'pa'}), \
                patch('sys.argv', ['workflow-vm.py', 'start', 'gtk-gl']):
            with self.assertRaisesRegex(RuntimeError, 'audio mode differs'):
                vm.main()
            wait.assert_not_called()

    def test_readiness_does_not_consume_command_stdin(self):
        vm = load('workflow-vm')
        with patch.object(vm, 'identity', return_value=(42, True, True, [])), patch.object(vm, 'ssh') as ssh:
            vm.wait_ssh(42)
            self.assertEqual(ssh.call_args.kwargs['stdin'], subprocess.DEVNULL)
            self.assertLessEqual(ssh.call_args.kwargs['timeout'], 10)

    def test_start_missing_kernel_reports_log(self):
        # No QEMU is started: launcher fails before touching a disk.
        result = subprocess.run(['bash', str(SCRIPTS.parent / 'vm.sh'), 'start', 'serial'],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('serial.log', result.stderr)
        self.assertIn('Missing kernel', (self.root / 'logs/workflow/serial.log').read_text())

    def test_non_qemu_port_collision(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            env = dict(os.environ, SSH_PORT=str(listener.getsockname()[1]))
            result = subprocess.run(['bash', str(SCRIPTS.parent / 'vm.sh'), 'start', 'serial'],
                                    env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Address already in use', result.stderr)

    def test_restart_probe_accepts_time_wait(self):
        listener=socket.socket()
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind(('127.0.0.1',0));listener.listen()
        port=listener.getsockname()[1]
        peer=socket.create_connection(('127.0.0.1',port))
        accepted,_=listener.accept()
        accepted.close()  # Active close leaves the server port in TIME_WAIT.
        peer.recv(1);peer.close();listener.close()
        with socket.socket() as probe:
            with self.assertRaises(OSError):probe.bind(('127.0.0.1',port))
        result=subprocess.run(['bash',str(SCRIPTS.parent/'vm.sh'),'start','serial'],
                              env=dict(os.environ,SSH_PORT=str(port)),text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('Address already in use',result.stderr)
        self.assertIn('Missing kernel',(self.root/'logs/workflow/serial.log').read_text())

    def test_missing_archive_before_privileged_setup(self):
        env = dict(os.environ, ARCHIVE_DIR=str(self.root / 'missing-archives'))
        result = subprocess.run(['bash', str(SCRIPTS.parent / 'setup.sh'), 'source'],
                                env=env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('https://github.com/christianhaitian/dArkOS/releases', result.stdout + result.stderr)
        self.assertNotIn('sudo:', result.stderr)

    def test_invalid_prepare_option_before_boot(self):
        result = subprocess.run(['bash', str(SCRIPTS.parent / 'sdk.sh'), 'prepare', '--unknown'],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Usage:', result.stderr)
        self.assertFalse((self.root / 'state/vm.json').exists())

    def test_runtime_import_regenerates_shell_profile(self):
        import shlex
        bundle = load('workflow-bundle')
        source=self.root/'bundle'; source.mkdir()
        subprocess.run(['qemu-img','create','-f','qcow2',str(source/'runtime.qcow2'),'1M'],check=True,capture_output=True)
        for name in ['Image','runtime-id','LICENSES.txt','provenance.json']:
            (source/name).write_text('test fixture')
        (source/'profile.json').write_text(json.dumps({'root_partuuid':'9aef4565-02','root_fstype':'btrfs','root_partition':'2','boot_partuuid':None,'roms_partuuid':None}))
        marker=self.root/'untrusted-profile-executed'
        (source/'profile.env').write_text('touch '+shlex.quote(str(marker)))
        bundle.seal(source,'runtime')
        work=self.root/'import'; disk=work/'images/work.qcow2'; kernel=work/'Image'
        env=dict(os.environ,WORK_DIR=str(work),DISK_IMAGE=str(disk),KERNEL_IMAGE=str(kernel))
        result=subprocess.run(['python3',str(SCRIPTS/'bundle.py'),'import-runtime',str(source)],env=env,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(marker.exists())
        self.assertIn('ROOT_PARTUUID=9aef4565-02',(work/'state/profile.env').read_text())
        self.assertNotIn('touch',(work/'state/profile.env').read_text())
    def test_bundle_corruption(self):
        bundle = load('workflow-bundle')
        path = self.root / 'file'
        path.write_text('original')
        bundle.seal(self.root, 'sdk')
        bundle.verify(self.root, 'sdk')
        path.write_text('corruption')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            bundle.verify(self.root, 'sdk')

    def test_bundle_traversal(self):
        bundle = load('workflow-bundle')
        (self.root / 'bundle.json').write_text(json.dumps({'format': 1, 'kind': 'sdk', 'files': {'../outside': 'bad'}}))
        with self.assertRaisesRegex(ValueError, 'path failure'):
            bundle.verify(self.root, 'sdk')

    def test_bundle_can_be_reexported(self):
        bundle = load('workflow-bundle')
        (self.root / 'file').write_text('data')
        bundle.seal(self.root, 'sdk')
        bundle.seal(self.root, 'sdk')
        bundle.verify(self.root, 'sdk')

    def test_incomplete_runtime(self):
        bundle = load('workflow-bundle')
        bundle.seal(self.root, 'runtime')
        with self.assertRaisesRegex(ValueError, 'Missing bundle'):
            bundle.verify(self.root, 'runtime')

    def test_sdk_absolute_link(self):
        sdk = load('workflow-sdk')
        (self.root / 'link').symlink_to('/usr/lib')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            sdk.inventory(self.root)

    def test_sdk_relative_link_and_relocation(self):
        sdk = load('workflow-sdk')
        (self.root / 'file').write_text('data')
        (self.root / 'link').symlink_to('file')
        before = sdk.inventory(self.root)
        renamed = self.root.with_name(self.root.name + '-moved')
        self.root.rename(renamed)
        try:
            self.assertEqual(before, sdk.inventory(renamed))
        finally:
            renamed.rename(self.root)

    def test_private_pkgconfig_prefix(self):
        (self.root / 'usr/include').mkdir(parents=True)
        private = self.root / 'opt/darkos-graphics/usr/lib/aarch64-linux-gnu/pkgconfig'
        private.mkdir(parents=True)
        path = private / 'sdl2.pc'
        path.write_text('prefix=/usr\nlibdir=${prefix}/lib/aarch64-linux-gnu\n')
        command = ['python3', str(SCRIPTS / 'es-sysroot.py'), str(self.root)]
        subprocess.run(command, check=True)
        first = path.read_text()
        subprocess.run(command, check=True)
        self.assertEqual(first, path.read_text())
        self.assertIn('prefix=/opt/darkos-graphics/usr', first)

if __name__ == '__main__':
    unittest.main()
