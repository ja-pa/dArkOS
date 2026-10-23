# Standalone QEMU user releases

Stop the prepared development VM, then run from the repository root:

```bash
./make_qemu_release.sh --dry-run
./make_qemu_release.sh
# Optional destination parent:
./make_qemu_release.sh --output-root "/path with spaces/releases"
```

Defaults: `WORK_DIR=$HOME/darkos-g350-qemu-v08272026`, its `images/work.qcow2` and
`build/arch/arm64/boot/Image`, and `qemu/locks/g350-v08272026.json`.
`WORK_DIR`, `DISK_IMAGE`, `KERNEL_IMAGE`, `RELEASE_LOCK` can be specified in the
environment. The selected lock must match the prepared runtime record.
No guest rebuild or download is performed. Prepare the runtime using the
[QEMU guide](../README.md) first. Export requires Python 3.11+, qemu-img, qemu-nbd,
util-linux, Btrfs tools and sudo for mounting the exported copy.

Example output:

```text
dist/qemu/darkos-qemu-g350-trixie-02012026-g172967430b47/
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

Editable launchers and documentation live in `qemu/packaging/templates/`. Packaging
adds the existing controls helper, audio helper, controls mapping and G350 photo
from `qemu/scripts/`, `qemu/config/` and `qemu/assets/`, using an explicit copy list. Guest-only
payloads and cleanup live under `qemu/packaging/guest/`. Development tools, SDK, SSH keys
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

## Archiv a GitHub Release

Po exportu ponechte původní složku bez spuštění a testujte její kopii. VM mění
`darkos.qcow2` už při bootu. Balicí skript vyžaduje původní `SHA256SUMS`, čistý
commitovaný export a vypnutou VM. Použitý nebo pozměněný disk standardně odmítne; pro otestovaný disk
použijte `--clean-tested-disk` (viz níže). Samotné přepsání součtů nenahrazuje
čištění dat. Logy uvnitř guestu, SSH klíče a testovací
save soubory čistí už `make_qemu_release.sh` na exportované kopii. Pokud už byl spuštěn jediný export, lze zabalit jeho vyčištěnou kopii.

```bash
release=dist/qemu/darkos-qemu-g350-trixie-09022026-gfa2420dca4f0
cp -a -- "$release" "$HOME/release test"
# Otestujte kopii, potom ji řádně vypněte přes její stop.sh.
bash archive_qemu_release.sh "$release" --dry-run
bash archive_qemu_release.sh "$release"
# Volitelně jiné zapisovatelné umístění:
bash archive_qemu_release.sh "$release" --output-root "$HOME/GitHub release assets"
```

Výchozí výstup je `dist/qemu/github/<release_id>/`. Obsahuje díly
`<release_id>.tar.gz.001`, `.002`, …, jejich `SHA256SUMS` a český `RELEASE.md`
s příkazy pro stažení a rozbalení. Vedle je `upload-draft.sh` pro nahrání na GitHub. Jméno a revize pochází
z `provenance.json` exportu, nikoli z aktuálního checkoutu balicího skriptu.

Do archivu jde jen pevný seznam souborů původního exportu. `.runtime`, logy,
screenshoty a jiné přidané soubory se nezabalí. Zdrojové soubory se nemažou ani
neupravují; balení pouze používá `.runtime/state/` pro stejné zámky jako launcher.
Při běhu drží zámky proti startu VM, ověřuje samostatnost QCOW2 a `qemu-img check`.
Před balením i po něm ověřuje zdrojové součty a celý spojený archiv znovu přečte
včetně hashů jednotlivých souborů. Existující výstup ani `.partial` nepřepisuje.

Komprimovaný tar se zapisuje přímo do dílů, bez velkého mezilehlého archivu.
Předem se kontroluje místo na cílovém filesystemu i fyzickém C: ve WSL;
konzervativní rezerva je velikost všech vstupních souborů plus 256 MiB.
Při čištění testovaného disku je rezerva dvojnásobek virtuální velikosti disku
plus 256 MiB, protože se vytváří i pracovní QCOW2.
Výchozí díl má nejvýše **1 900 MiB**. `--part-size-mib` dovoluje 1 až 2047 MiB.
[GitHub vyžaduje soubory menší než 2 GiB a nejvýše 1000 assetů](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

Pro kontrolu a rozbalení stáhněte všechny díly a `SHA256SUMS` do jedné složky:

```bash
sha256sum -c SHA256SUMS
cat darkos-qemu-*.tar.gz.[0-9][0-9][0-9] | tar -xz
# V rozbalené složce ještě před prvním spuštěním:
sha256sum -c SHA256SUMS
```

Používejte konkrétní jméno archivu uvedené ve vygenerovaném `RELEASE.md`,
pokud je ve složce více vydání. Na Windows tyto příkazy spusťte v Ubuntu WSL.

Po instalaci GitHub CLI a `gh auth login` nahrajte koncept:

```bash
bash /cesta/k/assetům/upload-draft.sh NOVY_TAG
```

Helper nejprve ověří součty a zavolá `gh release create --draft` s přesnou revizí
exportu a explicitním seznamem assetů. Nahraje jen díly, součty a uživatelský
`RELEASE.md`; sám sebe nenahrává. Koncept zkontrolujte a publikujte v GitHub UI.
Samotné balení nic nenahrává ani nepublikuje a nepotřebuje přístupový token.

### Balení již otestované složky

```bash
sudo -v
bash archive_qemu_release.sh "/cesta/release po testech" --clean-tested-disk
```

Tento režim přijme změněný disk, ale stále požaduje nezměněné ostatní soubory
včetně původního `SHA256SUMS` a `provenance.json`. Zdrojový disk musí být vypnutý,
samostatný a projít kontrolou. Skript zkopíruje payload do pracovního adresáře,
zkopíruje samostatný QCOW2 a připojí **pouze tuto kopii**. Přes `sudo -n`
použije stejný NBD/mount postup jako exportér. Potřebuje stejné závislosti
jako export a platné přihlášení sudo (nejprve `sudo -v` ve stejném terminálu).
Kontrola sudo proběhne před kopírováním disku.

Z kopie odstraní guest logy, SSH identitu a klíče, historii shellu a testovací
RetroArch/ROM save soubory. Instalované hry a konfigurace ponechá. Nemění
launchery, kernel ani verze komponent. Nové součty a záznam
`distribution_cleanup` v `provenance.json` zachycují původní součet testovaného
disku, hashe čisticích skriptů a rozsah čištění. Jméno výstupu získá `-cleaned`.
Hostitelské logy a stav se opět nezabalí. Původní testovaná složka se nemaže.

Na rozbalené kopii vyčištěného balíčku ověřte první start a vypnutí před
publikováním; vyčištěný disk se po tomto testu opět nebalí přímo. Pracovní kopie
se po úspěchu odstraní, při chybě zůstává v `.partial` pro diagnostiku.

Při dlouhém kopírování může přihlášení sudo vypršet. V takovém případě spusťte celý
příkaz jako root: `sudo bash archive_qemu_release.sh "/cesta/release" --clean-tested-disk`.
Souborové výstupy pak vlastní root; zůstávají čitelné běžnému uživateli.
