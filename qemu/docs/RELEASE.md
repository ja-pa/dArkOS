# Create a standalone user release

[Documentation index](../README.md)

Use this workflow for an end-user package without a checkout, SDK or development
SSH access. For transferable development environments, see [SDK bundles](SDK.md).
Commands run from the repository root in Ubuntu WSL unless stated otherwise.

## Prepare and export

Complete [Build](BUILD.md), review [local validation](MAINTENANCE.md#local-validation),
and stop the development VM. Use a clean committed checkout for public releases.

```bash
export WORK_DIR="$HOME/darkos-g350-qemu-v08272026"
bash qemu/vm.sh stop
./make_qemu_release.sh --dry-run
./make_qemu_release.sh
# Optional destination parent:
./make_qemu_release.sh --output-root "/path with spaces/releases"
```

Defaults are the selected work directory's `images/work.qcow2` and
`build/arch/arm64/boot/Image`, with `qemu/locks/g350-v08272026.json`.
`WORK_DIR`, `DISK_IMAGE`, `KERNEL_IMAGE` and `RELEASE_LOCK` may override them;
the lock must match the prepared runtime. Export does not download or rebuild.
Host requirements include Python 3.11+, qemu-img, qemu-nbd, util-linux, Btrfs tools
and sudo for mounting the copy.

Output defaults to `dist/qemu/<release_id>/`, for example
`darkos-qemu-g350-trixie-09022026-g<commit-prefix>`. The input filename supplies
the image version. Provenance records the full packaging commit; a dirty checkout
adds a content hash covering tracked changes and nonignored untracked files.
Runtime build metadata is recorded separately from packaging identity.

The exporter makes a compressed independent QCOW2, sanitizes only that copy,
installs automatic ES startup and power-button shutdown, and copies the kernel.
It verifies disk integrity, absence of a backing file and delivered checksums
before renaming `.partial`. Existing final/partial directories are never replaced;
failed partial output stays available for inspection. Allow at least the virtual
disk size plus 1 GiB of temporary space. Keep the source disk stopped throughout.

Host launchers and the bundled README come from `qemu/packaging/templates/`;
controls/audio helpers and assets are copied explicitly from the QEMU source tree.
Export-only guest payloads are under `qemu/packaging/guest/`. The package includes
license/source notices and provenance, but excludes the SDK, development tools,
checkout and SSH identity.

## Acceptance before distribution

Keep the original export unbooted and test a complete copy in a path containing
spaces. A boot changes `darkos.qcow2`, so its release checksum stops matching.
Verify first/repeated automatic ES starts, the actual controls window, games,
save/load across reboot, audio, duplicate-start protection and clean shutdown.
Run `qemu-img check` on the stopped test copy afterward. Host unit tests do not
replace these guest/GUI checks. Record failures and limitations with the results.

User commands are `start.sh`, `controls.sh` and `stop.sh`. `--no-controls` and
`QEMU_AUDIO=none` are supported. Settings/saves persist in the disk; logs and
locks go to `.runtime/`. No host SSH port is forwarded. The included README has
dependencies, keyboard/PICO-8 instructions and WSLg recovery commands.

## Split archives and GitHub draft

```bash
release="/path/to/untouched-release"
cp -a -- "$release" "$HOME/release test"
# Test the copy and shut it down using its stop.sh.
bash archive_qemu_release.sh "$release" --dry-run
bash archive_qemu_release.sh "$release"
# Optional destination:
bash archive_qemu_release.sh "$release" --output-root "$HOME/GitHub release assets"
```

The default output is `dist/qemu/github/<release_id>/`, containing
`<release_id>.tar.gz.001`, `.002`, etc., `SHA256SUMS`, English `RELEASE.md`
instructions and `upload-draft.sh`. Name/revision come from the export's
`provenance.json`, not the archiving checkout. Public assets require an export
made from clean committed source and a stopped VM.

Archiving accepts only the explicit payload list. Host logs, `.runtime`, screenshots
and unrelated additions are excluded. It uses the launcher's locks, verifies the
independent disk and checksums before/after archiving, and rereads the joined
archive including each member's hash. It does not overwrite final/partial output.
Source payloads remain unchanged; `.runtime/state/` is used for coordination.

Compressed tar data streams straight into parts. The default maximum part is
1900 MiB; `--part-size-mib` accepts 1 through 2047. Free-space allowance is total
input size plus 256 MiB, checked on the destination and Windows C: backing drive
where applicable. Clean-tested mode needs twice the virtual disk size plus
256 MiB because it creates another working QCOW2.

To verify and extract, download all parts and their `SHA256SUMS` into one folder:

```bash
sha256sum -c SHA256SUMS
cat darkos-qemu-*.tar.gz.[0-9][0-9][0-9] | tar -xz
# Inside the extracted folder, before first boot:
sha256sum -c SHA256SUMS
```

Use the exact archive name in the generated instructions if multiple versions
share a directory. Windows users run these commands inside Ubuntu WSL.

After installing GitHub CLI and authenticating with `gh auth login`:

```bash
bash /path/to/assets/upload-draft.sh NEW_TAG
```

The helper verifies checksums and invokes `gh release create --draft` for the
exact export commit. It uploads only parts, checksums and `RELEASE.md`; it does
not upload itself. Review/publish the draft in GitHub. Export/archiving alone
neither uploads nor publishes and requires no access token.

## Archive an already tested disk

Prefer an untouched export. If the only export has already been booted:

```bash
sudo -v
bash archive_qemu_release.sh "/path/to/tested-release" --clean-tested-disk
```

This accepts a changed disk while requiring all other payloads, original checksums
and provenance to remain intact. Merely rewriting checksums is not cleanup.
The source must be stopped, independent and pass disk checks. The tool copies the
payload and disk, mounts only the copy, and applies the export cleanup using
`sudo -n` and the same NBD/mount procedure. Sudo is checked before copying.

Cleanup removes guest logs, SSH identity/keys, shell history and test RetroArch/ROM
saves/states. Installed games and configuration remain. Launchers, kernel and
component versions are unchanged. New checksums and `distribution_cleanup` in
provenance record the original tested-disk hash, cleanup script hashes and scope.
The output name gains `-cleaned`. The source test folder is preserved.

Test first boot and shutdown on a disposable extracted copy of the cleaned
archive before publication. Do not archive that booted copy directly again.
Working copies are removed after success and retained in `.partial` after failure.
If sudo expires during a long copy, run the entire command as root with
`sudo bash archive_qemu_release.sh "/path/to/tested-release" --clean-tested-disk`;
the resulting files will be owned by root.
