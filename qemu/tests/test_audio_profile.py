"""Audio migration preserves both ES XML formats and user choices on reapply."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('audio_profile', Path(__file__).resolve().parents[1] / 'scripts/audio-profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class ProfileTests(unittest.TestCase):
    def test_retroarch_enables_alsa_and_preserves_other_options(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'retroarch.qemu.cfg'
            original = 'video_driver = "gl"\naudio_driver = "null"\naudio_enable = "false"\naudio_latency = "128"\n'
            path.write_text(original)
            profile.retroarch_audio(path)
            first = path.read_text()
            profile.retroarch_audio(path)
            self.assertEqual(path.read_text(), first)
            self.assertIn('audio_driver = "alsathread"', first)
            self.assertIn('audio_enable = "true"', first)
            self.assertIn('audio_latency = "128"', first)
            self.assertIn('video_driver = "gl"', first)
            self.assertEqual(path.with_name(path.name + '.before-qemu-audio').read_text(), original)

    def test_settings_migration_and_reapply(self):
        for rooted in (False, True):
            with self.subTest(rooted=rooted), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'settings.cfg'
                original = ('<bool name="EnableSounds" value="false" />\n'
                            '<bool name="VideoAudio" value="true" />\n'
                            '<bool name="BackgroundMusic" value="false" />\n'
                            '<string name="ThemeSet" value="my-theme" />\n')
                if rooted:
                    original = '<config>' + original + '</config>'
                path.write_text(original)
                profile.settings_audio(path, 'Intel', 'Master', True)
                first = path.read_text()
                profile.settings_audio(path, 'Intel', 'Master', False)
                self.assertEqual(path.read_text(), first)
                self.assertEqual(path.with_name(path.name + '.before-qemu-audio').read_text(), original)
                root = ET.fromstring('<wrapper>' + first.replace('<?xml version="1.0"?>', '') + '</wrapper>')
                if rooted:
                    root = root[0]
                for name, value in [('EnableSounds', 'true'), ('VideoAudio', 'true'),
                                    ('BackgroundMusic', 'false'), ('ThemeSet', 'my-theme'),
                                    ('AudioCard', 'hw:Intel'), ('AudioDevice', 'Master')]:
                    items = [x for x in root if x.get('name') == name]
                    self.assertEqual(len(items), 1)
                    self.assertEqual(items[0].get('value'), value)
                path.write_text(first.replace('name="EnableSounds" value="true"',
                                              'name="EnableSounds" value="false"'))
                profile.settings_audio(path, 'Intel', 'PCM', False)
                self.assertIn('name="EnableSounds" value="false"', path.read_text())


if __name__ == '__main__':
    unittest.main()
