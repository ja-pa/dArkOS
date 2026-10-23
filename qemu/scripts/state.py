"""Stage receipts include content fingerprints, dependencies and verified outputs."""
import hashlib,json,os,sys
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(4*1024*1024): h.update(b)
    return h.hexdigest()

def fingerprint(root,lock,previous,stage=None):
    groups={
      'import':['scripts/import.sh'],
      'inspect':['scripts/inspect.sh','scripts/inventory.py','scripts/release_versions.py','scripts/with-disk.sh'],
      'prepare':['scripts/prepare.sh','scripts/grow.sh','scripts/grow_layout.py','scripts/chroot-run.sh','scripts/with-disk.sh'],
      'graphics':['scripts/graphics.sh','scripts/graphics-guest.sh','scripts/chroot-run.sh','scripts/with-disk.sh'],
      'build-emulationstation':['scripts/build.sh','scripts/build-guest.sh','tests/helpers/capture.c','scripts/chroot-run.sh','scripts/with-disk.sh','patches/emulationstation/'],
      'build-retroarch':['scripts/build.sh','scripts/build-guest.sh','tests/helpers/capture.c','scripts/chroot-run.sh','scripts/with-disk.sh'],
      'build-351files':['scripts/build.sh','scripts/build-guest.sh','tests/helpers/capture.c','scripts/chroot-run.sh','scripts/with-disk.sh','patches/351files/'],
      'kernel':['scripts/kernel.sh','scripts/build-kernel.sh','scripts/common.sh','scripts/components.py','config/kernel/'],
      'image':['scripts/image.sh','scripts/prepare-runtime.sh','scripts/configure.py','scripts/strip-compilers.sh','scripts/manifest.py','scripts/components.py','scripts/inventory.py','scripts/grow.sh','scripts/grow_layout.py','scripts/with-disk.sh','scripts/chroot-run.sh','runtime/','tests/helpers/test-roms.py','tests/fixtures/test-roms.json','tests/helpers/install-test-roms.py'],
    }
    if stage in groups:
        paths=[root/'scripts/lib.sh',root/'scripts/state.py',root/'scripts/release_config.py',root/'scripts/space.py']
        for name in groups[stage]:
            p=root/name
            paths.extend(sorted(p.rglob('*')) if p.is_dir() else [p])
    else: paths=sorted(root.rglob('*'))
    files={str(p.relative_to(root)):digest(p) for p in paths if p.is_file() and p.suffix in ['.sh','.py','.patch','.json','.cmake','.fragment','.config','.c'] and 'reference' not in p.parts and '__pycache__' not in p.parts}
    if stage and stage.startswith('build-'):
        p=root.parent/('build_'+stage[6:]+'-qemu.sh')
        if p.exists():files['../'+p.name]=digest(p)
    files['release_lock']=digest(lock)
    if previous and Path(previous).exists(): files['dependency']=digest(previous)
    return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()

if __name__=='__main__':
    action,root,lock,receipt,previous,*outputs=sys.argv[1:]
    receipt=Path(receipt); fp=fingerprint(Path(root),lock,previous,receipt.stem)
    if action=='check':
        if not receipt.exists(): sys.exit(1)
        data=json.loads(receipt.read_text())
        if data['fingerprint']!=fp: sys.exit(1)
        for p,h in data['outputs'].items():
            if not Path(p).is_file() or digest(p)!=h: sys.exit(1)
        print('Verified stage: '+receipt.stem)
    elif action=='record':
        data={'fingerprint':fp,'outputs':{str(Path(p).resolve()):digest(p) for p in outputs}}
        tmp=receipt.with_suffix('.partial'); tmp.write_text(json.dumps(data,indent=2)+'\n'); tmp.replace(receipt)
