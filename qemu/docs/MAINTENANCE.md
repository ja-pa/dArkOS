# Maintain and validate the QEMU target

[Documentation index](../README.md)

## Architecture and scope

The official release filesystem is the input. The QEMU target lives in the
dArkOS fork alongside upstream build recipes; normal handheld targets stay
unchanged. Import verifies a read-only raw image, then separate build and runtime
QCOW2 overlays isolate compilation from the delivered guest. Independent exports
remove the backing-file dependency.

The guest uses a separately built QEMU `virt` ARM64 kernel, VirtIO devices and a
private Debian SDL2/Mesa/DRM prefix under `/opt/darkos-graphics`. Frontends and
351Files are rebuilt from pinned sources with QEMU patches/flags. Original cores,
themes and ROM layout are retained where runtime validation supports them.
Board services and launch hooks are masked or adapted instead of loading Mali,
RGA or libgo2 into the tested graphical processes.

ARM64 chroot builds through binfmt keep frontend recipes close to upstream;
the kernel and application SDK use host cross-compilers. Kernel configuration is
in `qemu/config/kernel/`. `qemu/config/controls.json` owns keyboard mappings and
help-window layout, with the G350 background in `qemu/assets/`. Restart the help
window after editing it. Release packaging reuses those assets and helpers.

The controls background is `qemu/assets/controls-template.png`, derived from
`qemu/assets/g350-replacement.png`; labels are rendered over its empty boxes.
Box coordinates use source-image pixels, text positions are fractions of a box,
diagram font sizes use image pixels and UI font sizes use Tk points. Per-box
`styles.label` and `styles.mapping` override text styles. `ControlsWindow` manages
the interface and `ControlsDiagram` renders the diagram in the single
`qemu/scripts/controls-window.py` implementation.

Maintain the reason for each compatibility patch and the upstream change that
would allow its removal. ARM32 applications, physical controllers, Kodi,
additional standalone emulators and catalogue-wide PortMaster compatibility
require separate acceptance work. QEMU on x86 TCG is not a G350 performance model.

## Release selection and component review

The current default is `qemu/locks/g350-v08272026.json` and
`$HOME/darkos-g350-qemu-v08272026`. `qemu/scripts/release_config.py` centralizes
selection for shell tools, diagnostics and packaging; the raw filename comes
from the lock. To reproduce the older input, select both its lock and a separate
work directory explicitly:

```bash
export RELEASE_LOCK="$PWD/qemu/locks/g350-v01302026.json"
export WORK_DIR="$HOME/darkos-g350-qemu-v01302026"
```

Review the selected components without importing, mounting, building or booting:

```bash
make qemu-components
RELEASE_LOCK=qemu/locks/new-release.json make qemu-components \
  PREVIOUS_LOCK=qemu/locks/g350-v08272026.json
```

The report shows original and target versions, repositories, source commits,
retained components and changed/unchanged pins. Unknown original versions remain
explicit. It also appears after inspection and before preparation/build, saved
as `$WORK_DIR/logs/components.md`. An unchanged pin still needs review.

`replacements` describes original and target versions. Original binary inventory
is tied to the input image and binary hashes. Version strings can support a
version label but do not establish full source provenance. See the
[v08272026 upgrade record](validation/UPGRADE-v08272026.md) for selected sources
and uncertainties. That record describes one migration, not current instructions.

## Upgrade to a new upstream release

1. Review upstream source changes and the new official image independently.
   A clean Git merge does not prove image compatibility.
2. Create a new lock with image/archive hashes, source repositories and full
   revisions. Review every retained version, original-version evidence and label;
   do not replace newer image components with older sources accidentally.
3. Inspect partitions, services, binaries and library dependencies.
   Evidence from a previous image is not proof about the new one.
4. Use a fresh `WORK_DIR`; run [the complete build](BUILD.md) and local validation
   below. Preserve old environments and exported packages.
5. Build/check the matching SDK and its demo, review manifests and loaded libraries,
   then package and test an independent user release using [Release](RELEASE.md).
6. Commit the verified source and record a post-build attestation. Add a dated
   validation report with exact input, tested revision, evidence and limitations.

Kernel builds, including direct `qemu/scripts/build-kernel.sh` calls, read
`sources.kernel.repo` and `sources.kernel.commit` from the selected lock.
`SOURCE_REPO` may provide a mirror containing the same commit. A checkout at
another revision is rejected without resetting it. `artifacts/kernel-source.json`
records the actual revision, transport repository and binary hash.

Stages hold an exclusive work lock and write receipts only after success.
Content fingerprints and verified output hashes decide reuse. Mounts and NBD
attachments use a private namespace and cleanup traps. Interrupted imports are
kept separately. Lock changes invalidate relevant receipts; ordinary VM startup
does not rebuild the guest. Insufficient disk space is an error, not a cleanup
request. Deliberate package refreshes belong in a fresh work directory.

## Local validation

```bash
make qemu-check
make qemu-test
```

There is no GitHub Actions workflow for this target. `qemu-check` runs Bash syntax,
host helper compilation with warnings as errors, Python compilation and regression
tests; it does not install packages, compile guest components or boot a VM.
Tk rendering checks need `DISPLAY`; environment-dependent skips must be reported.

`qemu-test` verifies prerequisite stages and can recreate invalid outputs. Its
integration checks include original GB/GBC, NES, SNES, GBA and Mega Drive cores,
save/load and return to the same ES process, library maps, graphical captures,
351Files, PortMaster/SDLPoP, PICO-8 and repeated cold boots. Consult actual logs for
what passed; a build or package export is not a successful integration run.
Fixture sources/licenses and hashes are under `qemu/tests/fixtures/`.

On the tested VirGL path, QMP has no CPU scanout surface. Integration uses
`qemu/tests/helpers/capture.c` to read the client EGL framebuffer; the capture
helper is loaded only for diagnostics. It is not part of normal startup.

With conversion stopped, the optional privileged failure/cleanup check is:

```bash
sudo env WORK_DIR="$WORK_DIR" bash qemu/tests/cleanup.sh
```

It deliberately fails a read-only stage with an orphan child and verifies
failure status, child termination and cleanup. `qemu/scripts/check-filesystem.sh`
checks Btrfs read-only on a stopped working disk; it does not repair the base.
Use [audio diagnostics](TROUBLESHOOTING.md#audio-diagnostics) for stereo/mute
checks and perform listening tests separately.

## Manifests and attestation

`artifacts/delta.json` records the lock, source revision, dirty status, component
hashes, packages and changed files. `logs/test-results.json` and other integration
results describe the tested runtime. Keep detailed logs outside Git; retain
compact evidence and dated reports under `docs/evidence/` and `docs/validation/`.
Do not relabel historical evidence as a test of another release.

After a complete build, SDK preparation, validation and source commit:

```bash
bash qemu/vm.sh stop
make qemu-attest
```

Attestation checks stage receipts, runtime identity and integration freshness,
then writes `artifacts/attestation.json` with the final source commit, SDK and
component hashes. It does not rebuild or modify the guest, and refuses missing
or stale required results. Recording it after the source commit avoids a
self-referential commit hash. Packaging records its own source identity and does
not replace runtime build provenance.
