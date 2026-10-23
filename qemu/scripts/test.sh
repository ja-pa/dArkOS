#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
source "$QEMU_DIR/scripts/workflow-common.sh"
find "$QEMU_DIR" -name '*.sh' -print0 | xargs -0 -n1 bash -n
python3 -m compileall -q "$QEMU_DIR"
python3 -m unittest discover -s "$QEMU_DIR/tests" -p 'test_*.py'
sha256sum -c "$WORK_DIR/state/base-image.sha256"
vm start gtk-gl
remote 'nmcli -g GENERAL.CONNECTION device show enp0s2 | grep -Fx "QEMU VirtIO Ethernet"'
python3 "$QEMU_DIR/tests/integration.py"
python3 "$QEMU_DIR/tests/filemanager.py"
python3 "$QEMU_DIR/tests/portmaster.py"
vm stop
# Verify a second cold boot and preserve the machine for normal user launches.
vm start gtk-gl
remote 'nmcli -g GENERAL.CONNECTION device show enp0s2 | grep -Fx "QEMU VirtIO Ethernet"'
remote 'test -e /dev/dri/card0; systemctl is-active ssh; findmnt /roms'
python3 "$QEMU_DIR/tests/portmaster.py" --cold
vm stop
qemu-img check "$DISK_IMAGE"
sha256sum -c "$WORK_DIR/state/base-image.sha256"
echo 'G350 boot, UI, cores, states, keyboard return and restart gates passed'
