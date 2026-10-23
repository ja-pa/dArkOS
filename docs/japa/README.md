# Japa: sestavení G350 QEMU portu na novém počítači

Osobní návod pro reprodukci našeho prostředí. Je oddělený od hlavního README
projektu; popisuje postup z releasového obrazu až po funkční VM, SDK a exporty.

Aktualizováno 23. 10. 2026. Technický stav, ke kterému se postup vztahuje:
`codex/qemu-arm64-v08272026`. Upstream základ je tag `v08272026`,
commit `9faeb5883ea6bb567d802ee8ca7333b6ce6c8854`.

**Nevytváříme celý oficiální dArkOS od začátku.** Stahujeme původní G350 obraz
z releasu, nad ním vytváříme pracovní QCOW2 a upravujeme prostředí pro QEMU.
Z tohoto počítače není potřeba přenášet hotový QCOW2 ani SDK.

Výchozí lock je `qemu/locks/g350-v08272026.json` a nový pracovní adresář
`$HOME/darkos-g350-qemu-v08272026`. Starý pracovní adresář se nepřepisuje.
ES a 351Files se překládají z novějších připnutých zdrojů. RetroArch zůstává
1.22.2 a QEMU kernel 5.10.226; původní hardwarový kernel obrazu je 4.4.189.
Skripty kontrolují volné místo ve WSL i na podkladovém C:. Při jeho nedostatku
končí bez mazání starých VM či exportů.

## 1. Co potřebuji

- Ubuntu ve WSL2 s WSLg; ověřené prostředí je Ubuntu 26.04 na Windows.
- Podporu NBD, Btrfs a ARM64 binfmt v hostitelském Linuxu.
- Přibližně 50 GB volného místa, pro pohodlnou práci ideálně 16 GB RAM počítače.
  Jde o praktickou rezervu, ne změřené minimum. Exporty vyžadují další kopie dat.
- Internet pro GitHub, Debian balíčky a první stažení volných testovacích ROM.
- Oba oficiální archivy G350 uvedené níže.

Repozitář i pracovní adresář musí být na nativním linuxovém filesystemu,
například pod `$HOME`. Nedávat je pod `/mnt/c`. Samotné vstupní archivy mohou
zůstat na Windows disku. Příkazy níže se spouštějí v Ubuntu, ne v PowerShellu.
Pokud na jiném počítači ještě není WSL2/WSLg, je potřeba jej nejprve připravit;
tento návod jeho instalaci ani výměnu kernelu WSL neautomatizuje.

## 2. Naklonovat naši větev

Pokud v čerstvém Ubuntu chybí Git:

```bash
sudo apt-get update
sudo apt-get install -y git
```

Pak:

```bash
mkdir -p "$HOME/projects"
cd "$HOME/projects"
git clone --branch codex/qemu-arm64-v08272026 https://github.com/ja-pa/dArkOS.git darkos-g350
cd darkos-g350
```

Větev se může dále vyvíjet. Pro pozdější reprodukci si poznamenej konkrétní
revizi pomocí `git rev-parse HEAD`; na druhém počítači lze přejít na tento commit
přes `git checkout --detach <commit>`. Historický commit `475c877` ještě neobsahuje
klávesový port 351Files popsaný v tomto aktualizovaném návodu.

## 3. Připravit hostitele

```bash
sudo bash qemu/scripts/setup-host.sh
```

Skript instaluje QEMU, nástroje pro disky, build nástroje, ARM64 cross-kompilátor,
Python a podporu grafické nápovědy. Neinstaluje ani nemění kernel WSL.

Ověřit potřebnou podporu hostitelského kernelu a ARM64 interpreter:

```bash
sudo modprobe nbd max_part=16
sudo modprobe btrfs
cat /proc/sys/fs/binfmt_misc/qemu-aarch64
```

Poslední soubor musí existovat a ukazovat povolený ARM64 interpreter.
Pokud `modprobe nbd` selže kvůli chybějícímu modulu, je potřeba nejprve vyřešit
podporu NBD v kernelu WSL. Instalace QEMU přes APT ji nenahradí. Pokud chybí nebo
není povolený binfmt interpreter, opravit registraci `qemu-user-binfmt` před buildem.
Grafické kroky vyžadují funkční WSLg; v terminálu má být nastavené `DISPLAY`.

## 4. Připravit vstupy a proměnné

Z [upstream releasu v01302026](https://github.com/christianhaitian/dArkOS/releases/tag/v08272026)
stáhnout oba soubory do stejného adresáře:

```text
dArkOS_G350_trixie_09022026.img.7z.001
dArkOS_G350_trixie_09022026.img.7z.002
```

Lze použít kopie našich již stažených archivů. Ručně je nerozbalovat;
pipeline ověří jejich SHA256, integritu archivu a výsledný obraz.

Použít nový terminál a nepřebírat proměnné ze starého RG353M portu nebo SDK:

```bash
cd "$HOME/projects/darkos-g350"

unset DISK_IMAGE KERNEL_IMAGE SSH_KEY SSH_PORT ES_SYSROOT QMP_SOCKET
unset BUILD_DIR KERNEL_SRC RELEASE_LOCK SOURCE_REPO IMAGE RAW_IMAGE

export WORK_DIR="$HOME/darkos-g350-qemu-v08272026"
export ARCHIVE_DIR="/mnt/c/Users/TVUJ_WINDOWS_UZIVATEL/Downloads/darkos-images"
export JOBS=4
```

`ARCHIVE_DIR` nahradit skutečnou cestou k oběma archivům. `WORK_DIR` musí být
nový, vyhrazený tomuto portu. Při navázání práce v dalším terminálu je potřeba
proměnné nastavit znovu. Výchozí `WORK_DIR` sice odpovídá příkladu, ale starý
exportovaný `WORK_DIR` má přednost — přesně na tom jsme již narazili.

## 5. Import a příprava disků

```bash
make qemu-import
make qemu-inspect
make qemu-prepare
```

- `qemu-import`: ověří archivy, rozbalí oficiální obraz a nastaví jej pouze pro čtení.
- `qemu-inspect`: zjistí oddíly, filesystemy, balíčky a další vlastnosti G350 obrazu.
- `qemu-prepare`: vytvoří samostatné build a runtime QCOW2, zvětší oba disky
  a ověří ARM64 chroot, DNS a APT.

Zvětšení přes `grow.sh` je automatické před první APT kontrolou a kompilací:
build disk dostane navíc 12 GiB, runtime 4 GiB. EASYROMS se zálohuje a přesune
na nový konec disku, ROOTFS se rozšíří. Původní `.img` se nemění.
Na čistém prostředí není potřeba `grow.sh` spouštět ručně.

## 6. Grafika, ES, RetroArch a kernel

```bash
make qemu-graphics
make qemu-build COMPONENT=emulationstation
make qemu-build COMPONENT=retroarch
make qemu-build COMPONENT=351files
make qemu-image
```

Grafický krok připraví Debian SDL2/Mesa/DRM a závislosti. ES, RetroArch a 351Files se
kompilují v ARM64 chrootu přes QEMU user-mode. Nebootuje při tom celá konzole.

`qemu-image` zajistí také sestavení připnutého kernelu 5.10.226 pro QEMU pomocí
hostitelského ARM64 cross-kompilátoru a připraví výsledný runtime. Zdroje kernelu
si na čistém počítači obstará automaticky; starý pracovní adresář nepotřebuje.
Původní ARM64 emulátorová jádra z obrazu zůstávají zachovaná.

## 7. Kontroly a běžné spuštění

```bash
make qemu-check
make qemu-test
```

`qemu-check` provádí lokální kontroly a regresní testy; nebootuje VM a nesestavuje
ES, RetroArch ani kernel. `qemu-test` ověří připravený runtime grafickými testy:
GB/GBC, NES, SNES, GBA a Mega Drive, save/load, návrat do ES a opakovaný boot.
Potřebuje WSLg a při prvním spuštění stáhne volné testovací ROM. Konverzní cíle
včetně `qemu-test` kontrolují své předchozí kroky; chybějící nebo neplatné výstupy
mohou způsobit jejich nové provedení. GitHub Actions workflow v této větvi není.

Pro běžné používání teď na tomto počítači spouštím z `~/projects/darkos-g350`:

```bash
cd "$HOME/projects/darkos-g350"
env -u DISK_IMAGE -u KERNEL_IMAGE -u SSH_KEY -u SSH_PORT -u ES_SYSROOT -u QMP_SOCKET WORK_DIR="$HOME/darkos-g350-qemu-v08272026" bash qemu/vm.sh es
```

`env -u` pro toto spuštění odstraní případné zděděné proměnné ze starého portu
nebo SDK. Explicitní `WORK_DIR` vybere naše aktuální G350 prostředí. Nastavení
rodičovského terminálu se tím nemění.

Otevře QEMU, ES a nápovědu s fotkou G350 a mapováním kláves. V nápovědě přepínat
mezi ES, ovládáním ve hře a 351Files. Klávesy posílat do okna QEMU, ne do okna nápovědy.
351Files používá šipky, Enter, Backspace, X pro nabídku, Insert pro označení
a Page Up/Down pro stránkování. Escape nebo F4 vrací do ES i z dialogu.
Nápovědu lze znovu otevřít přes `bash qemu/vm.sh controls`.

```bash
bash qemu/vm.sh ssh 'uname -a'
bash qemu/vm.sh stop
```

SSH používá klíč z pracovního adresáře a port `2232`. Starý port má `2222`.
Zvuk a fyzický gamepad zatím nejsou součástí ověřeného milníku.

## 8. SDK, záznam ověření a přenosné exporty

Volitelné pokračování po úspěšném buildu a integračních testech:

```bash
make qemu-sdk
bash qemu/vm.sh stop
make qemu-attest
```

Attestace ověřuje aktuálnost výsledků a zaznamená zdrojový commit, fingerprinty
a hashe artefaktů. Nenahrazuje předchozí integrační testy a vyžaduje zastavenou VM.

```bash
bash qemu/vm.sh export "$HOME/darkos-g350-runtime-export"
bash qemu/sdk.sh export "$HOME/darkos-g350-sdk-export"
```

Cílové adresáře exportů zatím nesmějí existovat. Runtime export obsahuje samostatný
QCOW2, kernel a metadata; nepotřebuje původní `.img`. Je to snímek, který se
pozdějšími změnami pracovního runtime automaticky neaktualizuje.

## Kde budou výsledky

Vše pod zvoleným `$WORK_DIR`:

| Cesta vůči WORK_DIR | Obsah |
|---|---|
| `images/dArkOS_G350_trixie_09022026.img` | Neměnný oficiální základ |
| `images/build.qcow2` | Prostředí pro závislosti a kompilaci |
| `images/work.qcow2` | Runtime používaný při běžném spuštění |
| `build/arch/arm64/boot/Image` | Kernel pro QEMU |
| `sources/` | Připnuté zdroje ES a RetroArchu |
| `artifacts/` | Binárky, balíčky, manifest a attestace |
| `sdk/` | SDK pro vývoj dalších aplikací |
| `logs/` | Logy přípravy, buildů a testů |
| `state/` | Profily a fingerprinty dokončených kroků |

Repozitář a pracovní adresář jsou dvě různé věci. Adresář `build` na hostiteli
obsahuje build kernelu; pracovní kompilace ES/RetroArchu jsou uvnitř `build.qcow2`.

## Zkrácená varianta a opakování

Po přípravě hostitele, archivů a proměnných provede hlavní konverzi a integrační
ověření jediný příkaz:

```bash
make qemu
```

SDK a exporty jsou samostatné kroky. Při první reprodukci je praktičtější jít
postupně podle návodu. Dokončené kroky se ověřují fingerprinty a hashi;
nezměněné platné kroky se neopakují. Při běžném selhání opravit příčinu a
zopakovat příslušný Make cíl; pipeline za neúspěšný krok nezapíše hotový výsledek.

## Co přesně znamená reprodukce

Obraz, archivy a zdrojové commity jsou připnuté. Čistý build ale stále používá
dostupné Debian repozitáře, takže na novém počítači může vyřešit jiné verze
některých balíčků než dnes. Ty se zaznamenají do manifestu a lokální cache.
Zatím nejde o záruku bitově shodného výsledného obrazu.

Další technické podrobnosti jsou v [QEMU README](../../qemu/README.md).

## Přehled změn při přechodu na další release

Bez buildu nebo spuštění VM zobrazit nahrazované komponenty:

```bash
make qemu-components
```

Porovnat připravovaný lockfile s dnešním základem:

```bash
RELEASE_LOCK=qemu/locks/novy-release.json make qemu-components \
  PREVIOUS_LOCK=qemu/locks/g350-v08272026.json
```

Tabulka ukáže původní a cílové verze, repozitáře, SHA a změněné i ponechané
revize. Neznámé původní verze jsou označené; údaje o verzi z jiného obrazu se
nepřebírají. Při konverzi se přehled vypíše po inspekci, před přípravou a buildem,
a uloží do `$WORK_DIR/logs/components.md`. Samotný přehled nic nepřestavuje.
Kernel už bere URL i SHA výhradně ze `sources.kernel` ve zvoleném lockfilu.
Pro další release použít nový pracovní adresář a projít i ponechané verze,
abychom novější obsah obrazu omylem nenahradili starší komponentou.
