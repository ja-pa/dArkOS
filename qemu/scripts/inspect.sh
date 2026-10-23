#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
if [[ ${1:-} != --mounted ]]; then
 with_disk "$RAW_IMAGE" ro bash "$0" --mounted
 exit
fi
out=$WORK_DIR/logs/inspect
mkdir -p "$out"
sfdisk --json "$NBD_DEVICE" > "$out/partitions.json"
lsblk -J -T -o PATH,TYPE,FSTYPE,LABEL,UUID,PARTUUID,SIZE "$NBD_DEVICE" > "$out/filesystems.json"
cp "$ROOT/etc/fstab" "$out/fstab"
cp "$ROOT/etc/os-release" "$out/os-release"
find "$ROOT/etc/systemd/system" -type l -printf '%P -> %l\n' | sort > "$out/services.txt"
find "$ROOT/etc/apt" -name '*.list' -o -name '*.sources' | while read -r p; do printf '\n%s\n' "${p#"$ROOT"}"; cat "$p"; done > "$out/apt-sources.txt"
[[ -z $BOOT_DEVICE ]] || mount -o ro "$BOOT_DEVICE" "$ROOT/boot"
[[ -z $ROMS_DEVICE ]] || mount -o ro "$ROMS_DEVICE" "$ROOT/roms"
python3 "$QEMU_DIR/scripts/release_versions.py" "$ROOT" "$out/versions.json"
python3 "$QEMU_DIR/scripts/inventory.py" "$ROOT" "$out/files.json"
python3 - "$ROOT" "$out" <<'PY'
import json,os,subprocess,sys,shlex
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2]); blocks=json.loads((out/'filesystems.json').read_text())['blockdevices']; facts=blocks[0].get('children',blocks[1:])
r=next(x for x in facts if x.get('label')=='ROOTFS')
boot=next((x for x in facts if x.get('label')=='BOOT'),None)
roms=next((x for x in facts if x.get('label')=='EASYROMS'),None)
profile={'root_partuuid':r['partuuid'],'root_fstype':r['fstype'],'boot_partuuid':boot['partuuid'] if boot else None,'root_partition':r['path'].split('p')[-1],'roms_partuuid':roms['partuuid'] if roms else None}
(out/'profile.json').write_text(json.dumps(profile,indent=2)+'\n')
state=out.parent.parent/'state'; (state/'profile.json').write_text(json.dumps(profile,indent=2)+'\n')
(state/'profile.env').write_text(''.join(f'export {k.upper()}={shlex.quote(str(v or ""))}\n' for k,v in profile.items()))
for src,name in [('etc/emulationstation/es_systems.cfg','es_systems.cfg'),('var/lib/dpkg/status','dpkg-status')]:
 p=root/src
 if p.exists(): (out/name).write_bytes(p.read_bytes())
rows=[]
for d in ['opt/retroarch','home/ark/.config/retroarch/cores','usr/bin/emulationstation']:
 p=root/d
 if not p.exists(): continue
 for f in sorted(p.rglob('*')):
  if f.is_symlink() or not f.is_file(): continue
  with f.open('rb') as s: magic=s.read(4)
  if magic!=b'\x7fELF': continue
  v=subprocess.check_output(['readelf','-h','-d',str(f)],text=True,stderr=subprocess.DEVNULL)
  rows.append({'path':'/'+str(f.relative_to(root)),'elf':v,'hardware_bound':any(x in v.lower() for x in ['libmali','librga','libgo2'])})
(out/'elf.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(profile,indent=2)); print('ELF files:',len(rows))
PY
