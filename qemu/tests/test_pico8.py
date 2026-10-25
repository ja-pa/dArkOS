"""PICO-8 profile, real launcher argv, and non-destructive Splore handling."""
import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

Q = Path(__file__).resolve().parents[1]

class Pico8Tests(unittest.TestCase):
    def test_profile_preserves_pico_and_other_systems_on_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'root'
            work = Path(folder) / 'work'
            def write(path, text):
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            selected = {'gb':'gambatte', 'gbc':'gambatte', 'nes':'fceumm',
                        'snes':'snes9x', 'gba':'mgba', 'megadrive':'genesis_plus_gx', 'pico-8':'fake08'}
            systems = ET.Element('systemList')
            for name, core in selected.items():
                system = ET.SubElement(systems, 'system')
                for tag, value in [('name', name), ('fullname', name), ('path', '/roms/'+name+('/carts/' if name=='pico-8' else '')),
                                   ('extension', '.png .PNG .p8 .P8' if name=='pico-8' else '.rom'),
                                   ('command', 'original'), ('theme', name), ('emulators', '')]:
                    ET.SubElement(system, tag).text = value
                write('home/ark/.config/retroarch/cores/'+core+'_libretro.so', 'fixture')
            write('etc/emulationstation/es_systems.cfg', ET.tostring(systems, encoding='unicode'))
            write('etc/fstab', 'original')
            write('home/ark/.emulationstation/es_settings.cfg', '<?xml version="1.0"?><string name="ThemeSet" value="original"/>')
            write('home/ark/.config/retroarch/retroarch.cfg', 'builtin_imageviewer_enable = "true"')
            (root/'opt/darkos-qemu').mkdir(parents=True)
            (work/'state').mkdir(parents=True)
            (work/'state/profile.json').write_text(json.dumps({'root_fstype':'btrfs'}))
            (work/'ssh').mkdir()
            (work/'ssh/id_ed25519.pub').write_text('test public key')
            with patch.dict(os.environ, ROOT=str(root), WORK_DIR=str(work)), patch('os.chown'):
                for _ in range(2):
                    runpy.run_path(str(Q/'scripts/configure.py'), run_name='__main__')
                    # Production runs as root; allow the unprivileged fixture's next pass.
                    (root/'etc/sudoers.d/qemu-development').chmod(0o640)
            tree = ET.parse(root/'etc/emulationstation/es_systems.cfg')
            found = {s.findtext('name'):s for s in tree.getroot()}
            self.assertEqual(set(found), set(selected)|{'ports'})
            pico = found['pico-8']
            self.assertEqual(pico.findtext('path'), '/roms/pico-8/carts/')
            self.assertEqual(pico.findtext('theme'), 'pico-8')
            self.assertEqual(pico.findtext('extension'), '.png .PNG .p8 .P8')
            for name, core in selected.items():
                self.assertEqual(found[name].findtext('command'), '/bin/bash /opt/darkos-qemu/retroarch.sh '+core+' %ROM%')
                self.assertIsNone(found[name].find('emulators'))
            self.assertTrue((root/'opt/darkos-qemu/pico8.cfg').is_file())
            self.assertIn('builtin_imageviewer_enable = "true"', (root/'home/ark/.config/retroarch/retroarch.cfg').read_text())

    def test_launcher_keeps_spaces_exit_status_and_scopes_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cores = root/'cores'; cores.mkdir()
            for core in ['fake08', 'gambatte']: (cores/(core+'_libretro.so')).touch()
            config = root/'pico8.cfg'; config.write_text((Q/'runtime/pico8.cfg').read_text())
            env = root/'env.sh'; env.write_text('exec python3 -c '+"'import sys; print(repr(sys.argv[1:])); sys.exit(37)'"+' "$@"')
            script = (Q/'runtime/retroarch.sh').read_text()
            for old,new in [('/home/ark/.config/retroarch/cores',str(cores)),
                            ('/home/ark/.config/retroarch',str(root/'config')),
                            ('/opt/darkos-qemu/env.sh',str(env)),
                            ('/opt/darkos-qemu/pico8.cfg',str(config))]: script=script.replace(old,new)
            launcher=root/'retroarch.sh'; launcher.write_text(script)
            cart=root/'Cart with spaces.P8.PNG'; cart.touch()
            import ast
            for core in ['fake08','gambatte']:
                result=subprocess.run(['bash',str(launcher),core,str(cart)],capture_output=True,text=True)
                self.assertEqual(result.returncode,37,result.stderr)
                args=ast.literal_eval(result.stdout)
                self.assertEqual(args[-1],str(cart))
                self.assertEqual('--appendconfig' in args,core=='fake08')
                if core=='fake08': self.assertEqual(args[args.index('--appendconfig')+1],str(config))
            sentinel=root/'ZZZSplore.P8.PNG';sentinel.touch()
            result=subprocess.run(['bash',str(launcher),'fake08',str(sentinel)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('Splore',result.stderr)

    def test_export_preserves_pico8_data_and_keeps_other_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            names=['roms/pico-8/carts/game.p8.png','roms/pico-8/carts/game.state',
                   'roms/pico-8/carts/game.srm','roms/pico-8/carts/cdata/game.p8d.txt',
                   'roms/gb/test.sav','roms/gb/test.state','roms/gb/test.gb']
            for name in names:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name)
            subprocess.run(['bash',str(Q/'packaging/guest/clean-rom-saves.sh')],
                           env=dict(os.environ,ROOT=str(root)),check=True)
            for name in names:
                path=root/name
                if name in ['roms/gb/test.sav','roms/gb/test.state']:self.assertFalse(path.exists())
                else:self.assertEqual(path.read_text(),name)

    def test_splore_is_disabled_without_touching_games_or_saves(self):
        spec=importlib.util.spec_from_file_location('pico8_configure',Q/'scripts/pico8-configure.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['zzzsplore.p8','ZZZSPLORE.P8.PNG','game.p8.png','game.srm']:(root/name).write_text(name)
            mod.disable_splore(root);mod.disable_splore(root)
            for name in ['zzzsplore.p8','ZZZSPLORE.P8.PNG']:
                self.assertFalse((root/name).exists())
                self.assertEqual((root/(name+'.qemu-disabled')).read_text(),name)
            for name in ['game.p8.png','game.srm']:self.assertEqual((root/name).read_text(),name)
            (root/'zzzsplore.p8').write_text('different')
            with self.assertRaisesRegex(RuntimeError,'Conflicting'):mod.disable_splore(root)
            self.assertEqual((root/'zzzsplore.p8').read_text(),'different')

if __name__ == '__main__': unittest.main()
