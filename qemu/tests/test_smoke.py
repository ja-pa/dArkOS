"""Smoke orchestration must not rebuild, reuse a VM, or overwrite full results."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

Q = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, Q / path)
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, 'path', [str(Q / 'tests'), *sys.path]):
        spec.loader.exec_module(module)
    return module


smoke = load('smoke', 'scripts/smoke.py')
integration = load('console_integration', 'tests/integration.py')


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='smoke with spaces ')
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        (self.work / 'state').mkdir()
        for name, content in {
            'profile.env': 'export ROOT_PARTUUID=test-02\nexport ROOT_FSTYPE=btrfs\n',
            'profile.json': json.dumps({'root_partuuid': 'test-02', 'root_fstype': 'btrfs'}),
            'image.json': json.dumps({'fingerprint': 'image-fingerprint'}),
            'runtime-id': 'runtime-id',
        }.items():
            (self.work / 'state' / name).write_text(content)
        self.env = dict(os.environ, WORK_DIR=str(self.work))
        for key, name in [('DISK_IMAGE', 'work.qcow2'), ('KERNEL_IMAGE', 'Image'), ('SSH_KEY', 'key')]:
            path = self.work / name
            path.write_text('prepared fixture')
            self.env[key] = str(path)
        self.vm = Mock()
        self.vm.identity.side_effect = [None, (42,), (42,)]
        self.full = self.work / 'logs/test-results.json'
        self.full.parent.mkdir()
        self.full.write_bytes(b'previous full validation\n')

    def test_profiles_select_one_or_all_systems_and_separate_outputs(self):
        systems, logs, result = integration.profile_settings(self.work, 'full')
        self.assertEqual(systems, ('gb', 'gbc', 'nes', 'snes', 'gba', 'megadrive'))
        self.assertEqual(result, self.full)
        systems, logs, result = integration.profile_settings(self.work, 'smoke')
        self.assertEqual(systems, ('gb',))
        self.assertTrue(logs.is_relative_to(self.work / 'logs/smoke'))
        self.assertTrue(result.is_relative_to(self.work / 'logs/smoke'))
        with patch.object(integration, 'run') as run, patch.object(sys, 'argv', ['integration.py']):
            integration.main()
        run.assert_called_once_with('full')

    def test_success_runs_only_smoke_and_preserves_full_results(self):
        with patch.object(smoke, 'load_vm', return_value=self.vm), patch.object(smoke, 'command') as command:
            result = smoke.run(self.work, self.env)
        self.assertTrue(result['passed'])
        self.assertTrue(result['clean_shutdown'])
        self.assertTrue(result['disk_checked'])
        calls = [call.args[0] for call in command.call_args_list]
        self.assertEqual(len(calls), 5)
        self.assertEqual(calls[0][-3:], ['start', 'gtk-gl', '--require-stopped'])
        self.assertEqual(calls[2][-3:], [str(Q / 'tests/integration.py'), '--profile', 'smoke'])
        self.assertEqual([calls[3][-1], calls[4][-1]], ['stop', 'check'])
        for call in command.call_args_list:
            self.assertEqual(Path(call.args[1]['QEMU_VM_LOG']), self.work / 'logs/smoke/serial.log')
        self.assertEqual(self.full.read_bytes(), b'previous full validation\n')
        self.assertEqual(result['runtime_id'], 'runtime-id')
        self.assertEqual(result['image_fingerprint'], 'image-fingerprint')

    def test_failed_scenario_keeps_diagnostics_and_never_claims_success(self):
        seen = []
        def fail(args, env, log):
            seen.append(args)
            if str(Q / 'tests/integration.py') in args:
                log.write('scenario failed\n')
                raise subprocess.CalledProcessError(1, args)
        with patch.object(smoke, 'load_vm', return_value=self.vm), patch.object(smoke, 'command', side_effect=fail):
            with self.assertRaises(subprocess.CalledProcessError):
                smoke.run(self.work, self.env)
        result = json.loads((self.work / 'logs/smoke/results.json').read_text())
        self.assertFalse(result['passed'])
        self.assertIn('error', result)
        self.assertEqual(len(seen), 3)  # No shutdown of a guest left for diagnosis.
        self.assertEqual(self.full.read_bytes(), b'previous full validation\n')
        self.assertIn('scenario failed', (self.work / 'logs/smoke/smoke.log').read_text())

    def test_unprepared_runtime_is_rejected_without_creating_it(self):
        missing = self.work / 'missing'
        with patch.object(smoke, 'command') as command:
            with self.assertRaisesRegex(RuntimeError, 'not prepared'):
                smoke.run(missing, self.env)
        command.assert_not_called()
        self.assertFalse(missing.exists())

    def test_running_vm_is_never_reused_or_stopped(self):
        self.vm.identity.side_effect = None
        self.vm.identity.return_value = (42,)
        with patch.object(smoke, 'load_vm', return_value=self.vm), patch.object(smoke, 'command') as command:
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                smoke.run(self.work, self.env)
        command.assert_not_called()
        self.assertFalse((self.work / 'logs/smoke').exists())

    def test_pipeline_lock_prevents_smoke_from_touching_guest(self):
        with (self.work / 'state/pipeline.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(smoke, 'load_vm') as vm:
                with self.assertRaisesRegex(RuntimeError, 'owns WORK_DIR'):
                    smoke.run(self.work, self.env)
            vm.assert_not_called()

    def test_changed_vm_identity_is_never_stopped(self):
        self.vm.identity.side_effect = [None, (42,), (43,)]
        with patch.object(smoke, 'load_vm', return_value=self.vm), patch.object(smoke, 'command') as command:
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                smoke.run(self.work, self.env)
        self.assertEqual(command.call_count, 3)
        self.assertFalse(json.loads((self.work / 'logs/smoke/results.json').read_text())['passed'])


if __name__ == '__main__':
    unittest.main()
