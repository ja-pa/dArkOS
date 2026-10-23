#!/usr/bin/env bash
# G350-specific capacity adjustment on disposable overlays. Preserve EASYROMS.
source "$(dirname "$0")/lib.sh"
if [[ ${1:-} != --mounted ]]; then
 disk=$(realpath "$1"); gib=${2:-12}
 [[ $disk == "$WORK_DIR/images/"*.qcow2 && $disk != "$RAW_IMAGE" ]] || fail 'Growth is restricted to working overlays'
 base_size=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["input"]["image_size"])' "$RELEASE_LOCK")
 target=$((base_size + gib * 1024 * 1024 * 1024))
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
python3 "$QEMU_DIR/scripts/grow_layout.py" "$WORK_DIR/state/$name.partition-before.json" "$WORK_DIR/logs/inspect/partitions.json" "$(blockdev --getsz "$NBD_DEVICE")" > "$WORK_DIR/state/$name.partition-new.sfdisk"

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
