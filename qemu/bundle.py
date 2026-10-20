"""Portable runtime/SDK bundles with verified manifests and image profiles."""
import json,os,shutil,subprocess as sp,sys,re,shlex
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'scripts'))
# Reuse the existing checksum and path validation helpers without executing CLI.
import importlib.util
spec=importlib.util.spec_from_file_location('bundles',Path(__file__).parent/'scripts/workflow-bundle.py'); helpers=importlib.util.module_from_spec(spec)
os.environ.setdefault('KERNEL_IMAGE',str(Path(os.environ['WORK_DIR'])/'build/arch/arm64/boot/Image'))
spec.loader.exec_module(helpers)
q=Path(__file__).parent; work=Path(os.environ['WORK_DIR']); disk=Path(os.environ['DISK_IMAGE']); kernel=Path(os.environ['KERNEL_IMAGE'])
action,arg=sys.argv[1:]; target=Path(arg).resolve()
def run(*args): sp.run(args,check=True)
def root(*args): run(*((['sudo'] if os.geteuid() else [])+list(args)))
if action.startswith('export-'):
 stage=target.with_name(target.name+'.partial')
 if target.exists() or stage.exists(): raise RuntimeError('Destination or partial export exists; choose a fresh destination')
 stage.mkdir(parents=True)
 if action=='export-runtime':
  # Reject live disks before conversion or sanitization.
  run('bash',str(q/'vm.sh'),'check')
  run('qemu-img','convert','-f','qcow2','-O','qcow2',str(disk),str(stage/'runtime.qcow2'))
  root('env','WORK_DIR='+str(work),'RELEASE_LOCK='+os.environ['RELEASE_LOCK'],'bash',str(q/'with-disk.sh'),str(stage/'runtime.qcow2'),'rw','bash',str(q/'sanitize.sh'))
  run('qemu-img','check',str(stage/'runtime.qcow2'))
  shutil.copy2(kernel,stage/'Image')
  for a,b in [('state/runtime-id','runtime-id'),('state/profile.json','profile.json'),('state/profile.env','profile.env'),('artifacts/delta.json','provenance.json')]: shutil.copy2(work/a,stage/b)
  if (work/'artifacts/attestation.json').exists(): shutil.copy2(work/'artifacts/attestation.json',stage/'attestation.json')
  if (work/'logs/test-results.json').exists(): shutil.copy2(work/'logs/test-results.json',stage/'validation.json')
  (stage/'LICENSES.txt').write_text('Local development export. Original package licenses remain in /usr/share/doc.\nSource revisions and changes: provenance.json; test ROM sources: accompanying qemu/test-roms.json.\nLinux: GPL-2.0; RetroArch: GPL-3.0; EmulationStation: see pinned source LICENSE. No new license grant.\n')
  helpers.seal(stage,'runtime')
 else:
  os.environ['ES_SYSROOT']=str(work/'sdk/sysroot')
  run(sys.executable,str(q/'scripts/workflow-sdk.py'),'check')
  shutil.copytree(work/'sdk',stage,dirs_exist_ok=True,symlinks=True)
  helpers.seal(stage,'sdk')
 stage.rename(target); print('Exported '+str(target))
elif action=='import-runtime':
 data=helpers.verify(target,'runtime')
 for name in ['profile.json','profile.env']:
  if name not in data['files']: raise RuntimeError('Missing required image profile: '+name)
 info=json.loads(sp.check_output(['qemu-img','info','--output=json',str(target/'runtime.qcow2')]))
 if info['format']!='qcow2' or 'backing-filename' in info: raise RuntimeError('Runtime bundle must be standalone qcow2')
 profile=json.loads((target/'profile.json').read_text())
 if profile.get('root_fstype') not in ['btrfs','ext4']: raise RuntimeError('Unsupported root filesystem')
 for field in ['root_partuuid','boot_partuuid','roms_partuuid']:
  value=profile.get(field)
  if (field=='root_partuuid' or value is not None) and not re.fullmatch(r'[a-fA-F0-9-]{4,64}',str(value)): raise RuntimeError('Invalid image partition identity')
 if not str(profile.get('root_partition','')).isdigit(): raise RuntimeError('Invalid root partition index')
 if disk.exists() or kernel.exists(): raise RuntimeError('Import needs a fresh WORK_DIR')
 disk.parent.mkdir(parents=True,exist_ok=True); kernel.parent.mkdir(parents=True,exist_ok=True)
 # Copy the sanitized base so the source bundle is never changed by rekeying.
 run('qemu-img','convert','-f','qcow2','-O','qcow2',str(target/'runtime.qcow2'),str(disk)+'.partial')
 shutil.copy2(target/'Image',kernel)
 for a,b in [('runtime-id','state/runtime-id'),('profile.json','state/profile.json'),('provenance.json','artifacts/delta.json')]:
  p=work/b; p.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(target/a,p)
 (work/'state/profile.env').write_text(''.join('export '+k.upper()+'='+shlex.quote(str(v or ''))+'\n' for k,v in profile.items() if k in ['root_partuuid','boot_partuuid','roms_partuuid','root_fstype','root_partition']))
 Path(str(disk)+'.partial').rename(disk)
 print('Imported runtime; configure local SSH identity before boot')
elif action=='import-sdk':
 helpers.verify(target,'sdk')
 sdk=work/'sdk'
 if sdk.exists(): raise RuntimeError('SDK already exists')
 shutil.copytree(target,sdk,symlinks=True)
 os.environ['ES_SYSROOT']=str(sdk/'sysroot'); run(sys.executable,str(q/'scripts/workflow-sdk.py'),'check')
else: raise RuntimeError('Unknown bundle action')
