#!/usr/bin/env bash
# Mounted only on a newly converted export copy.
set -euo pipefail
[[ $ROOT == "$WORK_DIR"/.mount.* && -f $ROOT/etc/darkos-qemu-profile ]]
find "$ROOT/etc/ssh" -maxdepth 1 -name 'ssh_host_*' -delete
find "$ROOT/home" "$ROOT/root" -type f \( -name authorized_keys -o -name known_hosts -o -name '.bash_history' \) -delete
find "$ROOT/var/log" -type f -exec truncate -s 0 -- {} +
truncate -s 0 "$ROOT/etc/machine-id"
rm -f "$ROOT/var/lib/dbus/machine-id" "$ROOT/var/lib/systemd/random-seed"
ln -s /etc/machine-id "$ROOT/var/lib/dbus/machine-id"
for dir in "$ROOT/home/ark/.config/retroarch/saves" "$ROOT/home/ark/.config/retroarch/states" "$ROOT/home/ark/.config/retroarch/logs"; do
 [[ ! -d $dir ]] || find "$dir" -mindepth 1 -type f -delete
done
sync
