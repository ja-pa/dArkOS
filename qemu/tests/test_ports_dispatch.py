"""Run the real dispatcher with isolated guest paths and a recording env adapter."""
from pathlib import Path
import subprocess
import tempfile
import unittest

Q = Path(__file__).resolve().parents[1]

class PortsDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ports = self.root / 'roms/ports'
        self.ports.mkdir(parents=True)
        profile = self.root / 'profile'
        profile.touch()
        env = self.root / 'env.sh'
        env.write_text('export PORTS_TEST_ENV=ready\nexec "$@"\n')
        script = (Q / 'runtime/ports.sh').read_text()
        for old, new in [('/etc/darkos-qemu-profile', str(profile)),
                         ('/home/ark/.local/state/darkos-qemu', str(self.root / 'logs')),
                         ('/roms/ports', str(self.ports)),
                         ('/opt/darkos-qemu/env.sh', str(env))]:
            script = script.replace(old, new)
        self.script = self.root / 'ports.sh'
        self.script.write_text(script)

    def run_port(self, path):
        return subprocess.run(['bash', str(self.script), str(path)], capture_output=True)

    def test_spaces_uppercase_environment_cwd_and_exit_status(self):
        launcher = self.ports / 'Demo with spaces.SH'
        launcher.write_text('test "$PORTS_TEST_ENV" = ready || exit 91\n'
                            'test -f ./asset || exit 92\nexit 37\n')
        (self.ports / 'asset').touch()
        self.assertEqual(self.run_port(launcher).returncode, 37)

    def test_missing_directory_traversal_and_external_symlink_are_rejected(self):
        outside = self.root / 'outside.sh'
        marker = self.root / 'executed'
        outside.write_text(f'touch "{marker}"\n')
        link = self.ports / 'outside.sh'
        link.symlink_to(outside)
        directory = self.ports / 'directory.sh'
        directory.mkdir()
        for path in [link, self.ports / '../../outside.sh', directory,
                     self.ports / 'missing.sh', outside]:
            with self.subTest(path=path):
                self.assertEqual(self.run_port(path).returncode, 2)
        self.assertFalse(marker.exists())

if __name__ == '__main__':
    unittest.main()
