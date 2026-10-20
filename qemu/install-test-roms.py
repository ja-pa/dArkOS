"""Install only the checksum-verified freely licensed fixtures."""
import hashlib,json,os,shutil
from pathlib import Path
q=Path(__file__).parent; work=Path(os.environ['WORK_DIR']);root=Path(os.environ['ROOT'])
for item in json.loads((q/'test-roms.json').read_text()):
    source=work/'test-roms'/item['filename']
    if hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']: raise RuntimeError('Bad ROM checksum: '+str(source))
    systems=[item['system']]+(['gbc'] if item['system']=='gb' else [])
    for system in systems:
        target=root/'roms'/system;target.mkdir(exist_ok=True)
        shutil.copy2(source,target/item['filename'])
(root/'opt/darkos-qemu/test-roms.json').write_bytes((q/'test-roms.json').read_bytes())
