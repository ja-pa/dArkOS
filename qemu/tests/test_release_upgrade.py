"""Release selection and partition safeguards for the September G350 image."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

Q = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Q / 'scripts'))
from release_config import selection
from grow_layout import plan
from space import require_space


class UpgradeTests(unittest.TestCase):
    def test_new_release_is_default_and_image_is_derived(self):
        chosen = selection({})
        self.assertEqual(Path(chosen['RELEASE_LOCK']).name, 'g350-v08272026.json')
        self.assertEqual(Path(chosen['RAW_IMAGE']).name, 'dArkOS_G350_trixie_09022026.img')
        self.assertEqual(Path(chosen['WORK_DIR']).name, 'darkos-g350-qemu-v08272026')

    def test_old_lock_is_still_selectable(self):
        chosen = selection({'RELEASE_LOCK': str(Q / 'locks/g350-v01302026.json'), 'WORK_DIR': '/tmp/old release'})
        self.assertEqual(chosen['RAW_IMAGE'], '/tmp/old release/images/dArkOS_G350_trixie_02012026.img')

    def test_shell_and_python_share_selection_with_spaces(self):
        env = dict(os.environ, WORK_DIR='/tmp/release path', RELEASE_LOCK=str(Q / 'locks/g350-v01302026.json'))
        env.pop('RAW_IMAGE', None)
        shell = subprocess.check_output(['bash', '-c', 'source "$1/scripts/common.sh"; printf "%s" "$RAW_IMAGE"', 'bash', str(Q)], env=env, text=True)
        self.assertEqual(shell, selection(env)['RAW_IMAGE'])

    def test_versions_are_bound_to_the_new_image(self):
        new = json.loads((Q / 'locks/g350-v08272026.json').read_text())
        old = json.loads((Q / 'locks/g350-v01302026.json').read_text())
        self.assertNotEqual(new['input']['image_sha256'], old['input']['image_sha256'])
        for component in ('emulationstation', 'retroarch', 'kernel'):
            self.assertEqual(new['replacements'][component]['base_image_sha256'], new['input']['image_sha256'])

    def test_raw_import_rejects_another_image_before_mounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'wrong.img'
            image.write_bytes(b'wrong image')
            env = dict(os.environ, WORK_DIR=tmp, IMAGE=str(image))
            env.pop('RAW_IMAGE', None)
            env.pop('RELEASE_LOCK', None)
            result = subprocess.run(['bash', str(Q / 'scripts/import.sh')], env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Wrong image size', result.stderr)
            self.assertFalse((Path(tmp) / 'images/work.qcow2').exists())

    def test_low_space_is_reported_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp, patch('space.shutil.disk_usage') as usage:
            usage.return_value.free = 1
            with self.assertRaisesRegex(ValueError, 'Existing data was preserved'):
                require_space(tmp, 1024)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def baseline(self, identity):
        return {'partitiontable': {'label': 'dos', 'id': identity, 'partitions': [
            {'start': 32768, 'size': 204800, 'type': 'c', 'bootable': True},
            {'start': 237568, 'size': 15360000, 'type': '83'},
            {'start': 15597568, 'size': 614400, 'type': 'c'}]}}

    def test_growth_accepts_both_release_identities_and_preserves_id(self):
        for identity in ('0x9aef4565', '0x32d47912'):
            base = self.baseline(identity)
            text = plan(base, copy.deepcopy(base), 40_000_000)
            self.assertIn('label-id: ' + identity, text)
            self.assertIn('size=614400, type=c', text)
            self.assertEqual(base['partitiontable']['partitions'][2]['start'], 15597568)

    def test_growth_rejects_foreign_and_modified_overlays(self):
        base = self.baseline('0x32d47912')
        with self.assertRaises(ValueError):
            plan(self.baseline('0x9aef4565'), base, 40_000_000)
        modified = copy.deepcopy(base)
        modified['partitiontable']['partitions'][1]['size'] += 1
        with self.assertRaises(ValueError):
            plan(modified, base, 40_000_000)
