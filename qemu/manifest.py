"""Generated attestation is outside Git; never self-reference a source commit."""
import hashlib,json,os,subprocess
from pathlib import Path
from inventory import inventory
from components import verified_kernel
root=Path(os.environ['ROOT']); work=Path(os.environ['WORK_DIR']); q=Path(__file__).parent
before=json.loads((work/'logs/inspect/files.json').read_text()); after=inventory(root)
# Exclude this generated attestation to avoid hashing its own previous version.
before.pop('/opt/darkos-qemu/provenance.json',None);after.pop('/opt/darkos-qemu/provenance.json',None)
changes={p:{'before':before.get(p),'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)}
def git(*args): return subprocess.check_output(['git','-c','safe.directory='+str(q.parent),'-C',str(q.parent),*args],text=True).strip()
data={'schema':1,'release':json.loads((work/'state/resolved-release.json').read_text()),'fork_commit':git('rev-parse','HEAD'),'worktree_dirty':bool(git('status','--porcelain')),'runtime_id':(work/'state/runtime-id').read_text().strip(),'packages':(work/'artifacts/graphics/runtime-packages.lock').read_text(),'components':{},'changes':changes,'package_installation':'Debian runtime packages extracted into /opt/darkos-graphics; compiler packages purged from runtime','generated_exclusions':['/opt/darkos-qemu/provenance.json'],'validation':'See logs/test-results.json; packaging alone does not pass the milestone'}
data['partition_changes']={'profile':json.loads((work/'state/profile.json').read_text()),'working_layout':(work/'state/work.qcow2.partition-new.sfdisk').read_text() if (work/'state/work.qcow2.partition-new.sfdisk').exists() else None}
data['recipe_sha256']={str(p.relative_to(q.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(q.rglob('*')) if p.is_file() and p.suffix in ['.sh','.py','.c','.patch','.json','.cmake','.fragment'] and '__pycache__' not in p.parts and 'reference' not in p.parts}
for p in q.parent.glob('build*qemu.sh'): data['recipe_sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
for p in q.parent.glob('build_*-qemu.sh'): data['recipe_sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
kernel=Path(os.environ['KERNEL_IMAGE'])
data['kernel']={'sha256':hashlib.sha256(kernel.read_bytes()).hexdigest(),'config_sha256':hashlib.sha256((work/'build/.config').read_bytes()).hexdigest(),'source':verified_kernel(work/'artifacts/kernel-source.json',data['release'],kernel),'build_log':str(work/'logs/build-build.log')}
for name in ['emulationstation','retroarch','351files']:
 p=work/'artifacts'/name/name
 data['components'][name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':data['release']['sources'][name],'build_log':str(work/'logs'/('build-'+name+'.log'))}
(work/'artifacts/delta.json').write_text(json.dumps(data,indent=2)+'\n')
(root/'opt/darkos-qemu/provenance.json').write_text(json.dumps({k:v for k,v in data.items() if k!='changes'},indent=2)+'\n')
