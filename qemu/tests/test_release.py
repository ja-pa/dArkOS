import importlib.util
import json
import os
from unittest.mock import patch
from pathlib import Path
import subprocess as sp
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('user_release', REPO / 'qemu/packaging/package.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_image_version_and_code_id(self):
        self.assertEqual(release.release_name('dArkOS_G350_trixie_02012026.img', {'id': 'g123'}),
                         'darkos-qemu-g350-trixie-02012026-g123')

    def test_mismatched_runtime_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'differs'):
            release.validate_release({'input': {'source_board': 'g350'}}, {'input': {}})

    def test_non_g350_runtime_is_rejected(self):
        value = {'input': {'source_board': 'other'}}
        with self.assertRaisesRegex(ValueError, 'G350'):
            release.validate_release(value, value)

    def test_code_id_covers_tracked_and_untracked_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            def git(*args):
                sp.run(['git', '-C', tmp, *args], check=True, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
            git('init')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Test')
            (repo / 'recipe').write_text('one')
            git('add', '.')
            git('commit', '-m', 'initial')
            clean = release.code_identity(repo)
            self.assertFalse(clean['dirty'])
            (repo / 'recipe').write_text('two')
            dirty = release.code_identity(repo)
            self.assertTrue(dirty['dirty'])
            self.assertIn('-dirty-', dirty['id'])
            (repo / 'extra').write_text('three')
            self.assertNotEqual(dirty['id'], release.code_identity(repo)['id'])
            git('add', 'recipe')
            (repo / 'recipe').write_text('one')
            (repo / 'extra').unlink()
            self.assertTrue(release.code_identity(repo)['dirty'])

    def test_existing_release_and_partial_are_never_overwritten(self):
        resolved = {'input': {'source_board': 'g350', 'image_filename': 'dArkOS_G350.img'}}
        code = {'id': 'gtest'}
        for suffix in ('', '.partial'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / (release.release_name(resolved['input']['image_filename'], code) + suffix)
                target.mkdir()
                with patch.object(release, 'read', side_effect=[resolved, resolved, {}]), \
                        patch.object(release, 'code_identity', return_value=code), \
                        patch.object(release.sp, 'run') as run:
                    with self.assertRaisesRegex(ValueError, 'Refusing to overwrite'):
                        release.main(['--output-root', tmp])
                    run.assert_not_called()

    def test_package_is_allowlisted_and_has_photographic_controls(self):
        with tempfile.TemporaryDirectory(prefix='release with spaces ') as tmp:
            stage = Path(tmp)
            release.package(stage, {'root_partuuid': 'test', 'root_fstype': 'btrfs'})
            self.assertEqual({p.name for p in stage.iterdir()}, {
                'start.sh', 'stop.sh', 'controls.sh', 'README.md', 'LICENSES.txt',
                'scripts', 'config', 'G350-ROM-NOTICES.md'})
            self.assertEqual((stage / 'config/g350_picture.jpg').read_bytes(),
                             (REPO / 'qemu/assets/g350_picture.jpg').read_bytes())
            self.assertEqual(json.loads((stage / 'config/image.json').read_text())['root_partuuid'], 'test')
            self.assertEqual((stage / 'scripts/controls-window.py').read_bytes(),
                             (REPO / 'qemu/scripts/controls-window.py').read_bytes())
            release.seal(stage)
            (stage / 'start.sh').write_text('tampered')
            result = sp.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=stage, capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_dry_run_resolves_default_and_custom_output_without_exporting(self):
        import contextlib
        import io
        resolved = {'input': {'source_board': 'g350', 'image_filename': 'dArkOS_G350.img'}}
        with tempfile.TemporaryDirectory(prefix='release destination ') as folder:
            for options, parent in [([], REPO/'dist/qemu'), (['--output-root', folder], Path(folder))]:
                with self.subTest(options=options), \
                        patch.object(release, 'read', side_effect=[resolved, resolved, {}]), \
                        patch.object(release, 'code_identity', return_value={'id': 'glayouttest'}), \
                        patch.object(release, 'package') as package, \
                        contextlib.redirect_stdout(io.StringIO()) as output:
                    release.main(['--dry-run', *options])
                    target = Path(json.loads(output.getvalue())['output'])
                    self.assertEqual(target.parent, parent)
                    self.assertFalse(target.exists())
                    package.assert_not_called()

    def test_help_does_not_need_runtime(self):
        result = sp.run(['bash', str(REPO / 'make_qemu_release.sh'), '--help'],
                        cwd='/', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--dry-run', result.stdout)




vm_spec = importlib.util.spec_from_file_location('release_vm', REPO / 'qemu/packaging/templates/scripts/release-vm.py')
vm = importlib.util.module_from_spec(vm_spec)
vm_spec.loader.exec_module(vm)


class ReleaseLifecycleTests(unittest.TestCase):

    def test_stale_state_never_targets_unrelated_process(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / 'vm.json'
            state.write_text(json.dumps({'pid': os.getpid(), 'started': vm.process_start(os.getpid()), 'qmp': '/tmp/not-ours'}))
            with patch.object(vm, 'STATE', state):
                self.assertIsNone(vm.identity())
                with patch.object(vm, 'qmp_command') as qmp, patch.object(vm, 'controls'):
                    vm.stop()
                    qmp.assert_not_called()

    def test_release_environment_drops_development_paths(self):
        with patch.dict(os.environ, WORK_DIR='/old', ROOT_FLAGS='old', EXTRA_APPEND='init=/bin/sh', SSH_PORT='bad'):
            env = vm.environment('/tmp/release-qmp')
            for key in ('WORK_DIR', 'ROOT_FLAGS', 'EXTRA_APPEND', 'SSH_PORT'):
                self.assertNotIn(key, env)
            self.assertEqual(env['QMP_SOCKET'], '/tmp/release-qmp')

    def test_no_display_is_actionable(self):
        with patch.dict(os.environ, {'DISPLAY': '', 'WAYLAND_DISPLAY': ''}), patch.object(vm.shutil, 'which', return_value='/bin/tool'):
            with self.assertRaisesRegex(RuntimeError, 'No graphical display'):
                vm.start(False)

    def test_broken_wslg_is_reported_before_start(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'weston.log'
            log.write_text('rdp_allocate_shared_memory: Failed to open /mnt/shared_memory: Input/output error\nRDP backend: use_gfxredir = 0\n')
            with patch.dict(os.environ, DISPLAY=':0'):
                with self.assertRaisesRegex(RuntimeError, 'WSLg graphics redirection failed.*VM was not started'):
                    vm.check_display(log)

    def test_recovered_wslg_ignores_previous_backend_error(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'weston.log'
            log.write_text('rdp_allocate_shared_memory: Failed to open /mnt/shared_memory\nRDP backend: use_gfxredir = 0\nRDP backend: use_gfxredir = 1\n')
            with patch.dict(os.environ, DISPLAY=':0'):
                vm.check_display(log)

    def test_duplicate_start_cannot_launch_another_vm(self):
        with patch.object(vm, 'identity', return_value={'pid': 123}), patch.object(vm.sp, 'Popen') as launch:
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                vm.start(False)
            launch.assert_not_called()

    def test_shutdown_timeout_leaves_vm_running(self):
        with patch.object(vm, 'identity', return_value={'pid': 123, 'qmp': '/tmp/test'}), \
                patch.object(vm, 'qmp_command') as qmp, \
                patch.object(vm.time, 'monotonic', side_effect=[0, 121]), \
                patch.object(vm.sp, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'VM left running'):
                vm.stop()
            qmp.assert_called_once_with('/tmp/test', 'system_powerdown')
            run.assert_not_called()

    def test_busy_qmp_monitor_has_actionable_error(self):
        with patch.object(vm, '_qmp_command', side_effect=TimeoutError):
            with self.assertRaisesRegex(RuntimeError, 'close other QMP monitor clients.*VM left running'):
                vm.qmp_command('/tmp/occupied-qmp', 'system_powerdown')



if __name__ == '__main__':
    unittest.main()
