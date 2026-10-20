> Accepted implementation scope (2026-10-20): G350 / RK3326 release image, ES + RetroArch and six ARM64 system entries, keyboard-only and dummy audio. Historical RG353M findings below remain reference evidence, not G350 facts.

# dArkOS QEMU Port — Architecture Concept

**Status:** Implementation in `ja-pa/darkos`, branch `codex/qemu-arm64`; see `qemu/README.md` and generated validation results.
**Date:** 2026-10-20
**Audience:** Project contributors and Codex
**Scope:** Turning an **existing official dArkOS release image** into a functional ARM64 QEMU variant, with the smallest maintainable divergence from upstream.

> **Guiding principle:** dArkOS has already done the difficult work of assembling the Debian-based ARM system and gaming stack. We do **not** want to rebuild that distribution from scratch. We want a reproducible, release-aware *porting pipeline* that adapts the official release for QEMU, recompiling components that are tied to Rockchip/Mali as necessary.

## 1. Objective and success criteria

Given an official dArkOS release image (initial baseline: `dArkOS_G350_trixie_02012026.img` (G350 / RK3326)), produce a QEMU-bootable development/test image which:

1. Preserves the **original userspace, assets, configuration and emulator ecosystem** whenever they are not hardware-dependent.
2. Replaces board-specific boot, kernel, device, GPU and input integration with QEMU-compatible equivalents.
3. Rebuilds **known GPU-dependent components**, starting with EmulationStation and RetroArch, against an appropriate Mesa/DRM/SDL2 stack. This rebuild is an **expected core stage**, not an exceptional fallback.
4. Uses **official Debian ARM64 packages** for SDL2, Mesa, EGL/GLES, GBM and DRM where compatible; does not rebuild SDL2 merely because upstream dArkOS does.
5. Reuses the **upstream dArkOS build recipes and dependency sources** as much as practical, rather than maintaining an independent implementation of the distribution build.
6. Can port a **newer dArkOS release** through an understandable, reviewable process, reporting incompatibilities instead of silently breaking.
7. Records precise provenance and the changes made for every port release.
8. Preserves original input images; all modifications operate on working copies, snapshots or overlays.

The project's primary measure of maintainability is **the size and clarity of the necessary divergence from upstream**. Build time is important but secondary until measured.

## 2. Repositories and current assets

| Repository | Role |
| --- | --- |
| [`ja-pa/darkos_qemu`](https://github.com/ja-pa/darkos_qemu) | Existing working QEMU port, kernel/VM tooling, SDK, validation and experiments; valuable migration baseline |
| [`christianhaitian/dArkOS`](https://github.com/christianhaitian/dArkOS) | Distribution build logic and integration recipes; proposed long-lived fork base |
| [`christianhaitian/EmulationStation-fcamod`](https://github.com/christianhaitian/EmulationStation-fcamod) | Upstream EmulationStation sources |
| [`christianhaitian/rk3566_core_builds`](https://github.com/christianhaitian/rk3566_core_builds) | RetroArch, SDL2 and other chipset-oriented build recipes/sources |
| [`ja-pa/kernel_5_10_226`](https://github.com/ja-pa/kernel_5_10_226) | Currently tested source baseline for the ARM64 QEMU kernel |
| [`ja-pa/darkos-tools`](https://github.com/ja-pa/darkos-tools) | Earlier QEMU launch work |

Observed in the inspected upstream code:

- `build_rg353m.sh` orchestrates `bootstrap_rootfs-rk3566.sh`, `build_deps.sh`, `build_sdl2.sh`, `build_retroarch.sh`, `build_emulationstation-rk3566.sh`, etc.
- Upstream recipes run ARM commands through `call_chroot` against `Arkbuild`, as defined in `utils.sh`.
- `build_retroarch.sh` delegates builds to `${CHIPSET}_core_builds/builds-alt.sh` and carries additional tasks for cores, assets, shaders and device configurations.
- EmulationStation recipes choose branches based on device and configure/build inside chroot.
- Upstream `make devenv` builds an ARM64 development chroot using `debootstrap` + QEMU user-mode; this is a useful reference, **not** a complete ready-to-run QEMU image conversion pipeline.
- Upstream documentation says WSL is unsupported for its build process. That does **not** prove WSL2 lacks `chroot`; actual chroot/binfmt/bind-mount behavior must be tested on our Ubuntu WSL2 host.

Existing `darkos_qemu` functionality that must not be lost inadvertently:

- Boots official RG353M-based userspace under QEMU `virt` using a separately compiled ARM64 Linux 5.10.226 kernel.
- Preserves original raw image and uses writable QCOW2 overlay.
- Working VirtIO GPU / Mesa graphics path, native SDL2 KMSDRM, EmulationStation and Peanut-GB demo workflow.
- Existing `setup.sh`, `sdk.sh`, `build.sh`, `vm.sh`, SSH, diagnostics, runtime identity checks and validation scripts.
- Current `scripts/graphics-prepare.sh` already obtains Debian ARM64 graphics packages into a private prefix. This proves a relevant approach, not necessarily that every package can be safely installed over vendor-owned libraries.
- Host cross-compilation with GCC 12, CMake and Ninja already works and is fast; retain as a reference and potential per-component optimization.

## 3. Key architecture decisions

### D1 — Fork the **main dArkOS repository**

Maintain a GitHub fork of `christianhaitian/dArkOS` with a QEMU-focused development branch. Put QEMU target logic **beside the related upstream scripts** so conflicts and code changes are visible during reviews/merges.

Prefer target-specific files and small, well-contained extensions to common upstream scripts over wholesale copies of large upstream recipes.

**Do not immediately fork every external repo.** Track exact upstream source revisions; fork an external project only when a persistent source change is necessary.

### D2 — Input is a **release image**, not a clean Debian bootstrap

Unlike dArkOS upstream, our normal path starts from the already released image. Avoid rebuilding the entire OS, formatting new board images from scratch, downloading all cores/assets again, or replacing unaffected packages.

The upstream build system provides useful **recipes, conventions and source selection**; it is not automatically the correct orchestrator for every image-transformation stage.

### D3 — Use stage-based transformation in a working rootfs

Stages must have explicit preconditions, outputs, diagnostics, cleanup and provenance. The working rootfs is mounted/entered only as needed; it is not an unmanaged long-lived mutable chroot.

### D4 — Native ARM chroot first for compatibility, cross-build remains possible

Where upstream build scripts assume native ARM userspace, initially prefer an ARM64 chroot (QEMU user-mode / `binfmt_misc`) to minimize recipe divergence. This will be slower than native x86 cross-compilation, potentially substantially so.

**Do not remove the cross toolchain.** Evaluate it as an optional optimization for expensive components after functional native-chroot builds. Cross-compiling from an x86 host against the release-matched ARM64 sysroot remains valuable. A hybrid chroot/cross approach is possible but not assumed trivial.

### D5 — Debian graphics stack where feasible

Replace Mali-bound EGL/GLES/GBM/SDL2 linkage with compatible Debian Mesa/SDL2 packages. Keep exact versions **resolved against the release's configured Debian repositories**, not hard-coded into bespoke scripts.

Check package ownership, version alignment, ABI compatibility, loader paths, symlinks and backend behavior. Do not blindly overwrite vendor-provided files or assume APT automatically handles non-package-managed symlinks.

### D6 — Recompile EmulationStation and RetroArch as expected stages

These are known to depend on vendor-specific graphics assumptions in the original image. Retain upstream branches/sources and configuration where possible, but replace graphics flags/dependencies with QEMU-compatible ones. Recompile additional emulators/cores only when investigation identifies an actual requirement.

### D7 — Keep upstream merge and release image compatibility **separate concepts**

A new upstream *Git commit* is not automatically the source snapshot that produced a particular published `.img`. Branch tips and external dependency branches may move. Establish provenance where possible; when unknowable, record the chosen compatible source commit and clearly label its relation to the binary release as **unverified/approximate**.

### D8 — Prefer a small, reviewable toolchain

GNU Make can expose targets and dependency ordering; Shell should handle mount/chroot/package/build operations. Small dedicated programs (including existing Python utilities) can remain where they demonstrably add value for manifest validation, hashing or safe disk management; **do not introduce Python as a new orchestration framework**. Ansible is not a good primary fit for artifact-oriented build pipelines.

## 4. Proposed pipeline and states

```text
Official dArkOS release .img + verified hashes
                         |
                     00 import
                         v
                  immutable base
                         |
                     10 inspect
                         v
     discovered release facts + source mapping
                         |
                  20 prepare rootfs
                         v
              working rootfs / chroot
                         |
                 30 graphics packages
                         v
       Debian SDL2/Mesa/DRM/EGL/GBM runtime
                         |
                    40 rebuild
                         v
        EmulationStation + RetroArch + required
             hardware-dependent components
                         |
                   50 configure
                         v
       service/launcher/fstab/input QEMU changes
                         |
                     60 package
                         v
           bootable QEMU working image
                         |
                    70 validate
                         v
        verified result + change/provenance report
```

| Stage | Responsibility | Examples of outputs/checks |
| --- | --- | --- |
| `import` | Verify official archives/image and make immutable working baseline | SHA256, partition discovery, safe QCOW2/backing or isolated copy |
| `inspect` | Gather facts about *this* image | Debian codename, architectures, `dpkg-query`, GPU symlinks, `readelf`, services, fstab, package sources |
| `prepare-rootfs` | Attach/mount working filesystem; prepare ARM64 chroot | Safe mounts `/dev`, `/proc`, `/sys`; binfmt; cleanup traps; guest kernel must **not** be needed to run chroot |
| `graphics` | Adapt graphics ABI/runtime | Debian package resolution, replacement of vendor library paths, verified Mesa/SDL2/KMSDRM stack |
| `rebuild` | Build components using upstream sources/recipes adapted for QEMU | EmulationStation, RetroArch, build logs, architecture & dynamic dependency checks |
| `configure` | Adapt board-oriented runtime assumptions | Boot mounts, firstboot/service masks, launch scripts, virtual input/audio/device configuration |
| `package` | Produce/refresh QEMU bootable working disk | Separate overlay or independently exportable image; original remains unchanged |
| `validate` | Test system behavior | QEMU boot, SSH, DRM/KMS, ES/RetroArch startup, logs, filesystem integrity |

**Stage ordering is a proposal, not a rigid restriction.** Some build stages may need headers/SDK preparation before graphics installation, and runtime adjustments may be needed before a graphical test. Declare real dependencies as we learn them.

**Important isolation rule:** A partially failed stage must not become a successful result. Store stage status and hashes only after verification; cleanup mount points and locks even on failure. For recoverability, use snapshots/checkpoints or regenerable overlays as appropriate rather than copying the entire multigigabyte rootfs after every step.

## 5. How to reuse upstream recipes

Two complementary patterns are expected:

**A. Share an upstream recipe with a QEMU target choice**

For example, introduce `TARGET=qemu-arm64`, and branch only at the hardware-specific dependencies and flags. Keep normal `rk3566` behavior unchanged. This is attractive for smaller scripts that can be made configurable without spreading conditionals everywhere.

**B. Extract narrowly reusable helper stages**

For large, tightly coupled upstream recipes like `build_retroarch.sh`, identify a minimal common *fetch/source/build* step and separate unrelated packaging/download/system-configuration work. Avoid calling the whole existing script merely to rebuild a single executable.

Before implementation, map the exact call graph across the main dArkOS repo and `rk3566_core_builds` (including source versions/branches, generated artifacts, Mali/libgo2/RGA dependencies, target flags and install locations).

**No blanket assumption:** Fork + merge detects textual conflicts, but it does not catch semantic drift. Local regression tests remain essential; GitHub Actions is intentionally disabled.

## 6. Git strategy and release provenance

Suggested conventions (adjust names to repository reality):

- Fork: `ja-pa/dArkOS` (proposed; do not assume it already exists).
- Remote `upstream`: `christianhaitian/dArkOS`.
- One active integration branch such as `qemu`; keep the fork changes small and documented.
- Immutable tags for successful ports, e.g. `qemu/v01302026-r1`.
- Maintenance branches for older ports **only if** they need fixes after the main QEMU branch advances.
- Prefer normal upstream merges with reviewed conflict resolution and local checks, rather than keeping a permanent queue of opaque external patches.

Maintain **one release lockfile per supported input image**. Proposed structure:

```yaml
schema: 1
input:
  upstream_release: v01302026
  image_filename: dArkOS_G350_trixie_02012026.img
  image_sha256: "<measured SHA256>"
  source_board: g350
  debian_codename: trixie
sources:
  darkos:
    repo: https://github.com/christianhaitian/dArkOS
    upstream_commit: "<verified or selected SHA>"
    relationship_to_image: "verified | inferred | unknown"
  emulationstation:
    repo: https://github.com/christianhaitian/EmulationStation-fcamod
    commit: "<resolved SHA>"
  core_builds:
    repo: https://github.com/christianhaitian/rk3326_core_builds
    commit: "<resolved SHA>"
target:
  machine: qemu-virt
  architecture: arm64
  graphics: mesa
  default_build_mode: arm64-chroot
  kernel_source_commit: "<resolved SHA>"
```

This YAML is a **proposed schema**, not a record of verified release-specific SHA values. Pin package versions and sources by *resolved input metadata* or a generated build lock/manifest as needed. It is acceptable to record unknown provenance explicitly; do not invent a historic release commit.

**Avoid the self-referential commit problem:** Do not embed the SHA of the commit containing this same manifest into the manifest itself. Record the fork `qemu_commit` in an **annotated Git tag**, generated post-build attestation. The source tree's own commit SHA is inherently available from Git.

Every successful build should generate an additional **delta manifest** with:

- Original image SHA and upstream/source commits.
- Fork commit/tag and toolchain versions.
- Packages added/replaced (exact versions, architecture, repositories).
- Source components rebuilt (commit, flags, binary SHA, install path).
- Files added/removed/changed, especially `/etc`, launchers, systemd units and graphics libraries/symlinks.
- Tests performed, results, build logs and any known exceptions.

For each nontrivial QEMU change, document **why it exists** and **what future upstream change would make it unnecessary**.

## 7. Build system interface (illustrative, not yet implemented)

```bash
make qemu-inspect IMAGE=/path/to/original.img
make qemu-prepare IMAGE=/path/to/original.img
make qemu-graphics
make qemu-build COMPONENT=emulationstation
make qemu-build COMPONENT=retroarch
make qemu-image
make qemu-test

# Full pipeline once the separate stages are stable:
make qemu IMAGE=/path/to/original.img
```

Use declarative dependencies and stage fingerprints (image hash, configuration, source commits, build flags, relevant patches/changed scripts). A mere `.done` timestamp is insufficient for a mutable chroot/image. For external changes such as APT repository updates, either lock resolved versions or require an explicit refresh operation.

## 8. Upgrade process for a new dArkOS release

1. Import the official image without overwriting any previous release.
2. Generate a **fresh inspection report** and compare with the last known-good image.
3. Determine the appropriate upstream dArkOS and external source revisions; distinguish verified from best-effort mapping.
4. Merge new upstream changes into the fork's active QEMU branch and review semantic changes in shared recipes.
5. Re-run graphics adaptation and the required rebuild stages against the **new image's** userspace/sysroot.
6. Run full validation; diagnose missing libraries, ABI changes, service/launcher changes and new HW dependencies.
7. Review delta size and its causes. Avoid adding ad hoc version-specific exceptions unless necessary and documented.
8. Tag the working port, publish lockfile + generated delta/attestation, and retain the old working release.

**A clean Git merge is not proof of compatibility.** The full QEMU integration test is the release gate.

## 9. Risks and open questions

| Risk / question | Proposed resolution |
| --- | --- |
| ARM64 GCC under QEMU user-mode is much slower than cross-GCC | Benchmark the *same* EmulationStation and RetroArch source/config in native-ARM chroot vs cross-build; measure cold/warm builds, peak RAM and wall time |
| WSL2 chroot/binfmt/mount behavior | Test on the actual Ubuntu WSL2 environment; isolate mounts, use dedicated working filesystem, avoid upstream recommendations for global passwordless sudo |
| Upstream shell recipes assume a freshly built `Arkbuild` rootfs | Introduce an import/preparation adapter for released rootfs; do not run destructive bootstrap/partition stages |
| Upstream release source mapping is uncertain | Distinguish verified/inferred/unknown provenance, pin chosen reproducible source commits |
| SDL2/Mesa package conflicts with vendor libraries | Audit package ownership and symlink chains; prefer reversible local replacement and verify dynamic linking |
| Some RetroArch/libretro cores have hardware-specific dependencies | Inventory before deciding what else requires recompilation; do not rebuild every core by default |
| DRM/KMS, EGL or GPU behavior differs from target handheld | Test in QEMU with VirtIO+Mesa; keep hardware-only behavior documented as unsupported or not tested |
| Merge succeeds but new upstream semantics break QEMU | Pre-merge static checks plus QEMU smoke/integration tests, stage-specific validation |
| Large and fragile diffs in the fork | Factor common build steps, isolate platform-specific configuration, track delta size and rationale |
| Time spent optimizing build infrastructure rather than porting | First get upstream-style ARM64 chroot path working; only optimize cross-compilation after a measured bottleneck |

## 10. Initial implementation plan for Codex

**Phase 0 — Investigation, no refactor yet**

1. Inspect the current HEAD of `ja-pa/darkos_qemu` and the release-tagged upstream scripts for G350/RK3326, SDL2, EmulationStation, RetroArch and `rk3326_core_builds`.
2. Build a dependency/call graph and table: upstream stage → source repositories → graphics assumptions → install targets → reusable as-is / needs refactor.
3. Extract the smallest possible list of changes already needed to boot and display ES in the existing working QEMU VM; identify current Python scripts that are policy-coupled to hard-coded versions versus generic validation utilities.
4. Verify how to mount/copy a released Btrfs rootfs into a safe ARM64 chroot on the WSL2 host. Do not modify the original image or global host setup without explicit confirmation.
5. Produce a concrete short design review and a minimal working experiment plan before editing the upstream fork.

**Phase 1 — Controlled proof of concept**

1. Prototype `import → inspect → chroot` starting from the existing official RG353M image.
2. Use release-compatible Debian ARM64 SDL2/Mesa packages. Confirm how to override vendor GPU libraries cleanly.
3. Rebuild **one** GPU-dependent component (preferably EmulationStation, which is already known to work in the current QEMU environment), initially via ARM64 chroot and upstream sources/recipes.
4. Install into a disposable working image and run the existing QEMU graphical validation.
5. Record commands, exact artifacts, installed packages, modified files and timing.

**Phase 2 — Fork integration**

1. Establish the Git fork and `qemu` branch once the necessary seams in upstream scripts are understood.
2. Add a `qemu` target, stage scripts and input release manifest without duplicating the full upstream build.
3. Integrate RetroArch, then examine additional affected components/cores.
4. Add idempotence/recovery checks, version-aware metadata, smoke tests and upgrade tests.

**Phase 3 — Performance and release automation**

1. Compare emulated ARM64 and cross-compiled builds under equivalent dependency versions.
2. Keep the lowest-complexity approach that meets reasonable iteration times.
3. Automate release attestations, manifests, tags and reproducible checks where practical.

### Codex working constraints

- Do **not** rewrite the port in Python, introduce Ansible, or replace proven cross-compilation tooling merely for aesthetic consistency.
- Do **not** replace the original dArkOS distribution with a newly bootstrapped Debian image.
- Do **not** assume binary compatibility between Mali/libgo2/RGA and Mesa/VirtIO.
- Do **not** run upstream `build_rg353m.sh` or image formatting scripts unchanged against our released rootfs.
- Do **not** hard-code transient Debian package versions or upstream branch tips as if they defined an immutable release.
- Do **not** claim that a fork alone prevents upgrade regressions: require test gates.
- Preserve the existing verified QEMU baseline until a new pipeline can match or exceed its functionality.
- Prioritize **minimum sustainable upstream diff, correctness, reproducibility and upgradeability** over prematurely optimized orchestration.

## 11. Definition of done for the first milestone

The first milestone is complete when we can start from the **unchanged official G350 image**, enter a repeatable ARM64 build environment derived from that release, install Debian Mesa/SDL2 compatibility libraries, build EmulationStation with a documented QEMU variation of its upstream recipe, deploy it into a **separate** QEMU image and validate its operation. The system must emit a useful manifest and clean up mounts on both success and failure.

The accepted first milestone also includes RetroArch ARM64 and the original GB/GBC, NES, SNES, GBA and Mega Drive cores, keyboard controls, states and return to ES. Cross-compile optimization is subsequent work.

---

**Bottom line:** This project is a **release-to-QEMU port**, not a new Linux distribution. A manageable upstream fork owns the QEMU integration points; the official released filesystem remains our input; ARM64 chroot preserves upstream build conventions; and component-level cross-compilation remains an option whenever measurements justify its added complexity.
