import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess as sp
import os
import unittest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release_archive', REPO / 'qemu/packaging/archive.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArchiveTests(unittest.TestCase):
    def fixture(self, root):
        for name in module.REQUIRED - {'SHA256SUMS'}:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((name + '\n').encode())
        (root / 'provenance.json').write_text(json.dumps({
            'release_id': 'darkos-qemu-test-g123',
            'packaging': {'dirty': False, 'commit': '1' * 40}}))
        manifest = {name: module.sha(root / name) for name in module.REQUIRED - {'SHA256SUMS'}}
        (root / 'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name, digest in sorted(manifest.items())))
        return manifest

    def test_roundtrip_split_excludes_logs_and_preserves_source(self):
        with tempfile.TemporaryDirectory(prefix='archive with spaces ') as tmp:
            source = Path(tmp) / 'release'
            output = Path(tmp) / 'assets'
            source.mkdir()
            output.mkdir()
            manifest = self.fixture(source)
            (source / '.runtime/logs').mkdir(parents=True)
            (source / '.runtime/logs/qemu.log').write_text('private')
            (source / 'extra.txt').write_text('private')
            module.verify(source, module.inventory(source))
            parts = module.archive(source, output, 'darkos-qemu-test', 211)
            self.assertGreater(len(parts), 1)
            self.assertTrue(all(part.stat().st_size <= 211 for part in parts))
            expected = {**manifest, 'SHA256SUMS': module.sha(source / 'SHA256SUMS')}
            module.verify_archive(parts, 'darkos-qemu-test', expected)
            module.verify(source, manifest)
            self.assertEqual((source / '.runtime/logs/qemu.log').read_text(), 'private')
            # Missing and corrupted volumes must not pass verification.
            with self.assertRaises((OSError, ValueError, EOFError)):
                module.verify_archive(parts[:-1], 'darkos-qemu-test', expected)
            data = bytearray(parts[-1].read_bytes())
            data[-5] ^= 255
            parts[-1].write_bytes(data)
            with self.assertRaises((OSError, ValueError, EOFError)):
                module.verify_archive(parts, 'darkos-qemu-test', expected)

    def test_upload_uses_exact_assets_and_stops_on_bad_checksum(self):
        with tempfile.TemporaryDirectory(prefix='upload with spaces ') as tmp:
            folder = Path(tmp)
            part = folder / 'darkos-qemu-test.tar.gz.001'
            part.write_bytes(b'part')
            (folder / 'SHA256SUMS').write_text(module.sha(part) + '  ' + part.name + '\n')
            (folder / 'RELEASE.md').write_text('release notes')
            module.write_upload(folder, 'darkos-qemu-test', '1' * 40, [part])
            gh = folder / 'gh'
            gh.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > args\n')
            gh.chmod(0o755)
            env = {**os.environ, 'PATH': str(folder) + ':' + os.environ['PATH']}
            result = sp.run(['bash', str(folder / 'upload-draft.sh'), 'test-tag'],
                            cwd='/', env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = (folder / 'args').read_text().splitlines()
            self.assertIn('--draft', args)
            self.assertIn('test-tag', args)
            self.assertIn('1' * 40, args)
            self.assertIn(part.name, args)
            (folder / 'args').unlink()
            part.write_text('corrupt')
            result = sp.run(['bash', str(folder / 'upload-draft.sh'), 'test-tag'],
                            env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((folder / 'args').exists())

    def test_guest_cleanup_removes_test_data_and_preserves_games(self):
        with tempfile.TemporaryDirectory(prefix='guest cleanup ') as tmp:
            work = Path(tmp)
            root = work / '.mount.test'
            files = {
                'etc/darkos-qemu-profile': 'qemu', 'etc/machine-id': 'old',
                'etc/ssh/ssh_host_test': 'key', 'home/ark/.ssh/id_test': 'key',
                'root/.bash_history': 'history', 'opt/darkos-qemu/compiler-removal-plan.log': 'log', 'var/log/private.log': 'log',
                'home/ark/.emulationstation/es_log.txt': 'log',
                'home/ark/.config/retroarch/states/game.state': 'save',
                'roms/gb/game.srm': 'save', 'roms/gb/game.state1': 'save',
                'roms/ports/sdlpop/QUICKSAVE.SAV': 'save',
                'roms/gb/game.gb': 'game', 'roms/ports/sdlpop/config.ini': 'config'}
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            (root / 'var/lib/dbus').mkdir(parents=True)
            tools = work / 'bin'
            tools.mkdir()
            # Mount operations are stubbed; the fixture roms/ is already populated.
            for name in ('mount', 'umount', 'fstrim', 'sync'):
                command = tools / name
                command.write_text('#!/bin/sh\nexit 0\n')
                command.chmod(0o755)
            env = {**os.environ, 'ROOT': str(root), 'WORK_DIR': str(work),
                   'ROMS_DEVICE': '/dev/fixture', 'PATH': str(tools) + ':' + os.environ['PATH']}
            result = sp.run(['bash', str(REPO / 'qemu/packaging/guest/clean-tested-guest.sh')],
                            env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'roms/gb/game.gb').read_text(), 'game')
            self.assertEqual((root / 'roms/ports/sdlpop/config.ini').read_text(), 'config')
            for name in files.keys() - {'etc/darkos-qemu-profile', 'etc/machine-id',
                                        'roms/gb/game.gb', 'roms/ports/sdlpop/config.ini'}:
                self.assertFalse((root / name).exists(), name)
            self.assertEqual((root / 'etc/machine-id').read_text(), '')

    def test_changed_disk_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            manifest = self.fixture(source)
            (source / 'darkos.qcow2').write_text('used disk')
            with self.assertRaisesRegex(ValueError, 'darkos.qcow2'):
                module.verify(source, manifest)

    def test_manifest_cannot_admit_extra_files_or_traversal(self):
        for name in ('../secret', '/secret', '.runtime/logs/qemu.log', 'darkos.qcow2'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp)
                self.fixture(source)
                with (source / 'SHA256SUMS').open('a') as stream:
                    stream.write('0' * 64 + '  ' + name + '\n')
                with self.assertRaisesRegex(ValueError, 'Unexpected or duplicate'):
                    module.inventory(source)

    def test_symlink_payload_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self.fixture(source)
            (source / 'Image').unlink()
            (source / 'Image').symlink_to('/etc/hostname')
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                module.inventory(source)

    def test_running_vm_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            with module.stopped(source):
                with self.assertRaisesRegex(ValueError, 'running'):
                    with module.stopped(source):
                        self.fail('must not acquire a running VM lock')

    def test_size_limit_before_io(self):
        for size in (0, 2048, -1):
            with self.subTest(size=size), self.assertRaisesRegex(ValueError, 'Part size'):
                module.main(['/missing', '--part-size-mib', str(size)])

    def test_dirty_export_and_existing_assets_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            self.fixture(source)
            output = Path(tmp) / 'out'
            target = output / 'darkos-qemu-test-g123'
            target.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                module.main([str(source), '--output-root', str(output)])
            provenance = source / 'provenance.json'
            data = json.loads(provenance.read_text())
            data['packaging']['dirty'] = True
            provenance.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'clean committed'):
                module.main([str(source)])


if __name__ == '__main__':
    unittest.main()
