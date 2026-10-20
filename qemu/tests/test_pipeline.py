"""Critical artifact integrity and image-protection invariants."""
import importlib.util,json,os,subprocess,tempfile,unittest
from pathlib import Path
Q=Path(__file__).resolve().parents[1]
def load(name):
    s=importlib.util.spec_from_file_location(name,Q/(name+'.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
class IntegrityTests(unittest.TestCase):
    def test_recipe_dependency_and_lock_invalidate_receipt(self):
        state=load('state')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'build.sh').write_text('first'); lock=p/'lock.json';lock.write_text('{}'); dep=p/'parent';dep.write_text('first')
            first=state.fingerprint(p,lock,str(dep))
            (p/'build.sh').write_text('second'); self.assertNotEqual(first,state.fingerprint(p,lock,str(dep)))
            (p/'build.sh').write_text('first');dep.write_text('second');self.assertNotEqual(first,state.fingerprint(p,lock,str(dep)))
            dep.write_text('first');lock.write_text('{"v":2}');self.assertNotEqual(first,state.fingerprint(p,lock,str(dep)))
    def test_inventory_does_not_follow_absolute_guest_symlinks(self):
        inv=load('inventory')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'file').write_text('test'); (p/'outside').symlink_to('/etc'); (p/'dev').mkdir();(p/'dev/secret').write_text('skip')
            data=inv.inventory(p)
            self.assertEqual(data['/outside']['symlink'],'/etc');self.assertNotIn('/outside/passwd',data);self.assertNotIn('/dev/secret',data)
    def test_mount_rejects_invalid_mode_before_modprobe(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); disk=p/'base';disk.touch()
            env=dict(os.environ,WORK_DIR=t,QEMU_MOUNT_NAMESPACE='yes')
            # Even without root, cannot reach any mount or block-device mutation.
            x=subprocess.run(['bash',str(Q/'with-disk.sh'),str(disk),'invalid','true'],env=env,text=True,capture_output=True)
            self.assertNotEqual(x.returncode,0);self.assertFalse(list(p.glob('.mount.*')))
    def test_valid_input_cannot_bless_a_foreign_existing_base(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); work=p/'work';(work/'images').mkdir(parents=True)
            source=p/'source.img';source.write_bytes(b'good')
            base=work/'images/base.img';base.write_bytes(b'evil')
            lock=p/'release.json';lock.write_text(json.dumps({'input':{'image_filename':'base.img','image_size':4,'image_sha256':hashlib.sha256(b'good').hexdigest()}}))
            env=dict(os.environ,WORK_DIR=str(work),IMAGE=str(source),RELEASE_LOCK=str(lock))
            result=subprocess.run(['bash',str(Q/'import.sh')],env=env,text=True,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('pinned release hash',result.stderr)
            self.assertEqual(base.read_bytes(),b'evil')
            self.assertFalse((work/'state/resolved-release.json').exists())
    def test_g350_lock_has_verified_size_and_sources(self):
        v=json.loads((Q/'releases/g350-v01302026.json').read_text())
        self.assertEqual(v['input']['image_size'],8301576192)
        for src in v['sources'].values(): self.assertRegex(src['commit'],r'^[a-f0-9]{40}$')
if __name__=='__main__': unittest.main()
