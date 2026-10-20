"""Post-build source/artifact attestation; generated outside the source tree."""
import datetime,json,os,subprocess as sp,sys
from pathlib import Path
from state import digest
q=Path(__file__).parent;w=Path(os.environ['WORK_DIR']);lock=Path(os.environ['RELEASE_LOCK'])
def run(*args,**kw):return sp.check_output(args,text=True,**kw).strip()
# Check immutable stage outputs without rebuilding anything.
previous=''
for name in ['import','inspect','prepare','graphics']:
    receipt=w/'state'/(name+'.json')
    sp.run([sys.executable,str(q/'state.py'),'check',str(q),str(lock),str(receipt),previous],check=True)
    previous=str(receipt)
for name in ['build-emulationstation','build-retroarch','kernel']:
    sp.run([sys.executable,str(q/'state.py'),'check',str(q),str(lock),str(w/'state'/(name+'.json')),previous],check=True)
sp.run([sys.executable,str(q/'state.py'),'check',str(q),str(lock),str(w/'state/image.json'),str(w/'state/image-inputs.sha256')],check=True)
sp.run(['bash',str(q/'vm.sh'),'check'],check=True)
validation=json.loads((w/'logs/test-results.json').read_text())
if not validation.get('passed') or set(validation.get('systems',{}))!={'gb','gbc','nes','snes','gba','megadrive'}:raise RuntimeError('Run the complete QEMU integration gate first')
current_id=(w/'state/runtime-id').read_text().strip()
image_fingerprint=json.loads((w/'state/image.json').read_text())['fingerprint']
if validation.get('runtime_id')!=current_id or validation.get('image_fingerprint')!=image_fingerprint:raise RuntimeError('Validation belongs to another image profile; rerun make qemu-test')
files=[w/'artifacts/delta.json',w/'logs/test-results.json',Path(os.environ['KERNEL_IMAGE']),w/'artifacts/emulationstation/emulationstation',w/'artifacts/retroarch/retroarch',w/'artifacts/graphics/runtime-packages.sha256',w/'sdk/manifest.json']
git=['git','-c','safe.directory='+str(q.parent),'-C',str(q.parent)]
data={'schema':1,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fork_commit':run(*git,'rev-parse','HEAD'),'worktree_dirty':bool(run(*git,'status','--porcelain')),'release_lock_sha256':digest(lock),'runtime_id':current_id,'image_fingerprint':image_fingerprint,'files':{str(p.relative_to(w)):digest(p) for p in files},'validation':validation}
if (w/'logs/roundtrip.json').exists():data['bundle_roundtrip']=json.loads((w/'logs/roundtrip.json').read_text())
target=w/'artifacts/attestation.json';temp=target.with_suffix('.partial');temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(target)
print('Attestation recorded: '+str(target))
