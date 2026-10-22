#!/usr/bin/env bash
set -euo pipefail
# Run only from with-disk.sh's private mount namespace.
[[ -n ${ROOT:-} && $ROOT == "$WORK_DIR"/.mount.* ]] || exit 1
had_resolv=false
if [[ -e $ROOT/etc/resolv.conf || -L $ROOT/etc/resolv.conf ]]; then cp -a "$ROOT/etc/resolv.conf" "$ROOT/etc/resolv.conf.qemu-build-backup"; had_resolv=true; fi
cp -L /etc/resolv.conf "$ROOT/etc/resolv.conf.qemu-build-new"
mv "$ROOT/etc/resolv.conf.qemu-build-new" "$ROOT/etc/resolv.conf"
policy=$ROOT/usr/sbin/policy-rc.d
had_policy=false
if [[ -e $policy ]]; then cp -a "$policy" "$policy.qemu-build-backup"; had_policy=true; fi
printf '#!/bin/sh\nexit 101\n' > "$policy"; chmod +x "$policy"
cleanup() {
 if $had_resolv; then mv -f "$ROOT/etc/resolv.conf.qemu-build-backup" "$ROOT/etc/resolv.conf"; else rm -f "$ROOT/etc/resolv.conf"; fi
 if $had_policy; then mv -f "$policy.qemu-build-backup" "$policy"; else rm -f "$policy"; fi
}
trap cleanup EXIT
chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive JOBS="${JOBS:-4}" bash "$@"
