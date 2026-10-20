#!/usr/bin/env bash
# G350-specific capacity adjustment on disposable overlays. Preserve EASYROMS.
source "$(dirname "$0")/lib.sh"
if [[ ${1:-} != --mounted ]]; then
 disk=$(realpath "$1"); gib=${2:-12}
 [[ $disk == "$WORK_DIR/images/"*.qcow2 && $disk != "$RAW_IMAGE" ]] || fail 'Growth is restricted to working overlays'
 target=$((8301576192 + gib * 1024 * 1024 * 1024))
 size=$(qemu-img info --output=json "$disk" | python3 -c 'import json,sys;print(json.load(sys.stdin)["virtual-size"])')
 (( size >= target )) || qemu-img resize "$disk" "$target"
 with_disk "$disk" rw bash "$0" --mounted "$(basename "$disk")"
 exit
fi
name=$2
[[ ! -e $ROOT/etc/darkos-qemu-grown ]] || exit 0
backup=$WORK_DIR/images/$name.easyroms-backup
# Verify exactly the known G350 DOS layout before touching partition boundaries.
sfdisk --json "$NBD_DEVICE" > "$WORK_DIR/state/$name.partition-before.json"
python3 - "$WORK_DIR/state/$name.partition-before.json" "$NBD_DEVICE" <<'PY' > "$WORK_DIR/state/$name.partition-new.sfdisk"
import json,subprocess,sys
v=json.load(open(sys.argv[1]))['partitiontable']; p=v['partitions']
assert v['label']=='dos' and v['id']=='0x9aef4565' and len(p)==3
assert p[0]['start']==32768 and p[1]['start']==237568 and p[1]['type']=='83' and p[2]['size']==614400
sectors=int(subprocess.check_output(['blockdev','--getsz',sys.argv[2]]))
start=(sectors-p[2]['size'])//2048*2048
assert start>15597568
p[1]['size']=start-p[1]['start']; p[2]['start']=start
print('label: dos\nlabel-id: '+v['id']+'\nunit: sectors\n')
for x in p:
 print('start={}, size={}, type={}{}'.format(x['start'],x['size'],x['type'],', bootable' if x.get('bootable') else ''))
PY
if [[ ! -e $backup ]]; then
 dd if="${NBD_DEVICE}p3" of="$backup.partial" bs=4M status=none
 mv "$backup.partial" "$backup"
 sha256sum "$backup" > "$backup.sha256"
fi
sha256sum -c "$backup.sha256"
umount "$ROOT"
sfdisk --force "$NBD_DEVICE" < "$WORK_DIR/state/$name.partition-new.sfdisk"
blockdev --rereadpt "$NBD_DEVICE"
udevadm settle
dd if="$backup" of="${NBD_DEVICE}p3" bs=4M conv=fsync status=none
mount -t btrfs "$ROOT_DEVICE" "$ROOT"
btrfs filesystem resize max "$ROOT"
echo 'G350 working overlay: EASYROMS moved intact, ROOTFS expanded' > "$ROOT/etc/darkos-qemu-grown"
df -h "$ROOT"
