# Standalone QEMU user releases

Stop the prepared development VM, then run from the repository root:

```bash
./make_qemu_release.sh --dry-run
./make_qemu_release.sh
# Optional destination parent:
./make_qemu_release.sh --output-root "/path with spaces/releases"
```

Defaults: `WORK_DIR=$HOME/darkos-g350-qemu`, its `images/work.qcow2` and
`build/arch/arm64/boot/Image`, and `qemu/releases/g350-v01302026.json`.
`WORK_DIR`, `DISK_IMAGE`, `KERNEL_IMAGE`, `RELEASE_LOCK` can be specified in the
environment. The selected lock must match the prepared runtime record.
No guest rebuild or download is performed. Prepare the runtime using the
[QEMU guide](README.md) first. Export requires Python 3.11+, qemu-img, qemu-nbd,
util-linux, Btrfs tools and sudo for mounting the exported copy.

Example output:

```text
qemu-release/darkos-qemu-g350-trixie-02012026-g172967430b47/
```

The image filename supplies the version; provenance records the full Git commit.
A modified checkout adds `-dirty-<content hash>` covering the tracked diff and
nonignored untracked files. This identifies packaging code. The already built
runtime has separate build metadata, including any kernel/audio upgrade.
Use a clean committed checkout for releases intended for users.

The exporter creates a compressed, independent QCOW2, sanitizes only that copy,
installs ES autostart and power-button shutdown, and copies the kernel. It checks
disk integrity, absence of a backing file and all delivered checksums before
renaming the `.partial` directory. Existing final or partial folders are never
overwritten; failures retain the partial folder for inspection. Allow at least
the virtual disk size plus 1 GiB of free temporary space. The source disk stays
unchanged. Never boot or mutate it during export.

Editable launchers and documentation live in `qemu/release/templates/`. Packaging
adds the existing controls helper, audio helper, controls mapping and G350 photo
from `qemu/scripts/` and `qemu/config/`, using an explicit copy list. Guest-only
payloads and cleanup live under `qemu/release/`. Development tools, SDK, SSH keys
and the repository are excluded.

The finished folder is movable and self-contained. Use `./start.sh`,
`./controls.sh` and `./stop.sh`. The controls window includes the G350 photograph.
`--no-controls` and `QEMU_AUDIO=none` are supported. Logs and state live in
`.runtime/`. Settings and saves persist directly in `darkos.qcow2`; its published
checksum changes after use. Subsequent boots preserve settings. No-audio boots
skip HDA setup. No SSH port is forwarded. Host dependencies and troubleshooting
are documented in the bundled README.

Before handing a release to users, move a copy to a path containing spaces and
test first/repeated ES boots, games and saves, sound, controls, duplicate-start
protection and clean shutdown, followed by `qemu-img check`. Local Python tests
do not replace these GUI/guest checks. Export does not publish to GitHub or
produce native Windows launchers. License notices and source links are bundled.
