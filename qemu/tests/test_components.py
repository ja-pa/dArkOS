"""Release upgrades must select actual source commits and expose retained versions."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

Q = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('components', Q/'scripts/components.py')
components = importlib.util.module_from_spec(spec)
spec.loader.exec_module(components)


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads((Q/'locks/g350-v01302026.json').read_text())

    def test_report_compares_pins_and_flags_unknown_versions(self):
        old = copy.deepcopy(self.lock)
        self.lock['sources']['retroarch']['commit'] = 'a' * 40
        with tempfile.TemporaryDirectory() as tmp:
            text = components.report(self.lock, Path(tmp), old)
        self.assertIn('UNKNOWN (not established for this image)', text)
        self.assertIn('2.13.0.0 CHMOD', text)
        self.assertIn('a' * 40, text)
        self.assertIn('CHANGED', text)
        self.assertIn('UNCHANGED — review retention on image upgrade', text)
        self.assertIn('libretro cores', text)

    def test_foreign_image_inventory_is_not_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'state').mkdir()
            old = copy.deepcopy(self.lock)
            old['input']['image_sha256'] = 'f' * 64
            (root / 'state/resolved-release.json').write_text(json.dumps(old))
            text = components.report(self.lock, root)
            self.assertIn('inventory is excluded', text)

    def test_old_version_evidence_cannot_be_reused_for_new_image(self):
        self.lock['input']['image_sha256'] = 'a' * 64
        with tempfile.TemporaryDirectory() as tmp:
            text = components.report(self.lock, Path(tmp))
        self.assertIn('| retroarch | UNKNOWN (not established for this image) |', text)

    def test_malformed_kernel_sha_is_rejected(self):
        self.lock['sources']['kernel']['commit'] = 'master'
        with self.assertRaises(ValueError):
            components.kernel_source(self.lock)

    def test_kernel_builder_uses_selected_lock_and_records_actual_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'source'
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Test')
            (repo / 'file').write_text('one')
            git('add', '.')
            git('commit', '-qm', 'one')
            first = git('rev-parse', 'HEAD')
            (repo / 'file').write_text('two')
            git('commit', '-qam', 'two')
            second = git('rev-parse', 'HEAD')
            fake = root / 'bin'
            fake.mkdir()
            # Real Git clone/checkout; only expensive compilation is simulated.
            make = fake / 'make'
            options = 'SERIAL_AMBA_PL011 SERIAL_AMBA_PL011_CONSOLE PCI PCI_HOST_GENERIC VIRTIO_PCI VIRTIO_BLK VIRTIO_NET EFI_PARTITION BTRFS_FS DEVTMPFS DEVTMPFS_MOUNT DRM DRM_VIRTIO_GPU SOUND SND SND_PCM SND_PCI SND_HDA SND_HDA_CORE SND_HDA_INTEL SND_HDA_GENERIC'
            make.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\nb=Path(next(a[2:] for a in sys.argv if a.startswith("O=")))\nb.mkdir(parents=True,exist_ok=True)\n(b/".config").write_text(' + repr(''.join('CONFIG_' + o + '=y\n' for o in options.split())) + ')\np=b/"arch/arm64/boot/Image"\np.parent.mkdir(parents=True,exist_ok=True)\np.write_bytes(b"test kernel")\n')
            make.chmod(0o755)
            for name in ['gcc-12', 'aarch64-linux-gnu-gcc-12', 'flex', 'bison', 'bc']:
                p = fake / name
                p.write_text('#!/bin/sh\necho test-tool\n')
                p.chmod(0o755)
            # The real merge script is part of the pinned source checkout.
            script = repo / 'scripts/kconfig/merge_config.sh'
            script.parent.mkdir(parents=True)
            script.write_text('#!/bin/sh\nexit 0\n')
            git('add', '.')
            git('commit', '-qm', 'merge helper')
            first = git('rev-parse', 'HEAD')
            (repo / 'file').write_text('three')
            git('commit', '-qam', 'three')
            second = git('rev-parse', 'HEAD')
            lock = root / 'release.json'
            self.lock['sources']['kernel'].update(repo=str(repo), commit=first)
            lock.write_text(json.dumps(self.lock))
            work = root / 'work'
            env = dict(os.environ, PATH=str(fake) + ':' + os.environ['PATH'], WORK_DIR=str(work), RELEASE_LOCK=str(lock))
            for name in ['SOURCE_REPO', 'KERNEL_SRC', 'BUILD_DIR']:
                env.pop(name, None)
            def build():
                return subprocess.run(['bash', str(Q / 'scripts/build-kernel.sh')], env=env, text=True, capture_output=True)
            result = build()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = work / 'artifacts/kernel-source.json'
            image = work / 'build/arch/arm64/boot/Image'
            self.assertEqual(components.verified_kernel(receipt, self.lock, image)['actual_commit'], first)
            self.lock['sources']['kernel']['commit'] = second
            lock.write_text(json.dumps(self.lock))
            result = build()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unexpected kernel commit', result.stderr)
            with self.assertRaises(ValueError):
                components.verified_kernel(receipt, self.lock, image)
            # A fresh checkout follows the changed lock, not an old hardcoded SHA.
            env['KERNEL_SRC'] = str(root / 'new-checkout')
            result = build()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(components.verified_kernel(receipt, self.lock, image)['actual_commit'], second)
            image.write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                components.verified_kernel(receipt, self.lock, image)


if __name__ == '__main__':
    unittest.main()
