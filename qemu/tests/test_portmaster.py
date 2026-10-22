import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

Q = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('portmaster_package', Q/'scripts/portmaster.py')
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)

class PortMasterPackageTests(unittest.TestCase):
    def test_rejects_traversal_before_extracting_any_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root / 'bad.zip', 'w') as z:
                z.writestr('safe.txt', 'safe')
                z.writestr('../outside', 'unsafe')
            with self.assertRaises(ValueError):
                pm.extract(root / 'bad.zip', root / 'dest')
            self.assertFalse((root / 'dest/safe.txt').exists())
            self.assertFalse((root / 'outside').exists())

    def test_pilot_preserves_original_binary_and_hardware_launcher(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            q = root / 'qemu'
            (q / 'ports').mkdir(parents=True)
            (q / 'ports/SDLPoP.sh').write_text('portable launcher')
            out = root / 'artifacts/portmaster'
            out.mkdir(parents=True)
            with zipfile.ZipFile(out / 'PortMaster.zip', 'w') as z:
                z.writestr('PortMaster/version', 'test')
            with zipfile.ZipFile(out / 'sdlpop.zip', 'w') as z:
                z.writestr('SDLPoP.sh', 'original hardware launcher')
                z.writestr('sdlpop/prince.aarch64', b'original binary')
            lock = {key: {'url': 'must-not-download', 'sha256': pm.sha(out / name)}
                    for key, name in [('portmaster', 'PortMaster.zip'), ('sdlpop', 'sdlpop.zip')]}
            (q/'locks').mkdir()
            (q/'locks/portmaster.lock.json').write_text(json.dumps(lock))
            with patch.object(pm, 'Q', q):
                pm.prepare(root)
                digest = pm.sha(out / 'portable/sdlpop.zip')
                pm.prepare(root)
            self.assertEqual(digest, pm.sha(out / 'portable/sdlpop.zip'))
            with zipfile.ZipFile(out / 'portable/sdlpop.zip') as z:
                self.assertEqual(z.read('sdlpop/prince.aarch64'), b'original binary')
                self.assertEqual(z.read('sdlpop/launch-handheld.txt'), b'original hardware launcher')
                self.assertEqual(z.read('SDLPoP.sh'), b'portable launcher')
            with (out / 'sdlpop.zip').open('ab') as f:
                f.write(b'corruption')
            with patch.object(pm, 'Q', q), self.assertRaises(ValueError):
                pm.prepare(root)

if __name__ == '__main__':
    unittest.main()
