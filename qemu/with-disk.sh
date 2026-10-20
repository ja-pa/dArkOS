#!/usr/bin/env bash
# All mounts live in a private namespace; only the named qcow2 is writable.
set -euo pipefail
if [[ ${QEMU_MOUNT_NAMESPACE:-} != yes ]]; then
 exec unshare --mount --propagation private env QEMU_MOUNT_NAMESPACE=yes bash "$0" "$@"
fi
source "$(dirname "$0")/lib.sh"
(( EUID == 0 )) || fail 'with-disk requires root'
disk=$(realpath "$1"); mode=$2; shift 2
[[ $mode == ro || $mode == rw || $mode == chroot ]] || fail 'Invalid mount mode'
[[ $mode == ro || $disk != "$(realpath -m "$RAW_IMAGE")" ]] || fail 'Base image is immutable'
format=$(qemu-img info --output=json "$disk" | python3 -c 'import json,sys; print(json.load(sys.stdin)["format"])')
[[ $mode == ro || $format == qcow2 ]] || fail 'Writable mounts require qcow2'
exec 8>/run/lock/darkos-qemu-nbd.lock
flock 8
modprobe nbd max_part=16
nbd=
for p in /sys/class/block/nbd*; do [[ -e $p/pid ]] || { nbd=/dev/${p##*/}; break; }; done
[[ -n $nbd ]] || fail 'No free NBD device'
mount_dir=$(mktemp -d "$WORK_DIR/.mount.XXXXXX")
attached=false
stage_pid=
cleanup() {
 local status=$?
 trap - EXIT INT TERM
 # Child compilers/loggers must close their files before unmounting. They run
 # in their own session, separate from the NBD backend and all host processes.
 if [[ -n $stage_pid ]]; then
  kill -TERM -- "-$stage_pid" 2>/dev/null || true
  wait "$stage_pid" 2>/dev/null || true
 fi
 for attempt in {1..50}; do
  if ! mountpoint -q "$mount_dir"; then break; fi
  if umount -R "$mount_dir" 2>/dev/null; then break; fi
  sleep .1
 done
 if mountpoint -q "$mount_dir" && [[ -n $stage_pid ]]; then
  kill -KILL -- "-$stage_pid" 2>/dev/null || true
  sleep .2
  umount -R "$mount_dir" || status=1
 fi
 if mountpoint -q "$mount_dir"; then
  echo "Cleanup failed: $mount_dir is busy; $nbd remains attached for recovery" >&2
  exit 1
 fi
 if $attached; then qemu-nbd --disconnect "$nbd" || status=1; fi
 rmdir "$mount_dir" || status=1
 exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
args=(--format="$format" --connect="$nbd")
[[ $mode != ro ]] || args+=(--read-only)
qemu-nbd "${args[@]}" "$disk"
attached=true
for attempt in {1..100}; do [[ -b ${nbd}p1 ]] && break; sleep .1; done
udevadm settle
# Locate ROOTFS by filesystem label, never by the RG353M partition identity.
root_device=
boot_device=
roms_device=
for p in "${nbd}"p*; do
 [[ -b $p ]] || continue
 case $(blkid -s LABEL -o value "$p" || true) in ROOTFS) root_device=$p;; BOOT) boot_device=$p;; EASYROMS) roms_device=$p;; esac
done
[[ -n $root_device ]] || fail 'ROOTFS-labelled partition absent'
fstype=$(blkid -s TYPE -o value "$root_device")
opts=rw
if [[ $mode == ro ]]; then opts=ro; [[ $fstype != btrfs ]] || opts=ro,rescue=nologreplay; fi
mount -t "$fstype" -o "$opts" "$root_device" "$mount_dir"
export ROOT=$mount_dir ROOT_DEVICE=$root_device ROOT_FSTYPE=$fstype NBD_DEVICE=$nbd BOOT_DEVICE=$boot_device ROMS_DEVICE=$roms_device
if [[ $mode == chroot ]]; then
 [[ -f /proc/sys/fs/binfmt_misc/qemu-aarch64 ]] || fail 'Enable qemu-aarch64 binfmt first (qemu-user-binfmt)'
 for name in dev proc sys; do mount --rbind "/$name" "$ROOT/$name"; mount --make-rslave "$ROOT/$name"; done
 mount -t tmpfs tmpfs "$ROOT/run"
fi
setsid "$@" <&0 &
stage_pid=$!
wait "$stage_pid"; exit
