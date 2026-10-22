# dArkOS QEMU — uživatelský release

Samostatný ARM64 systém pro QEMU na Linuxu nebo Ubuntu ve Windows WSL2 s WSLg.
Kernel `Image` a disk `darkos.qcow2` jsou součástí balíčku. Vývojový repozitář,
SDK, kompilátor ani původní dArkOS image nejsou potřeba. Nativní Windows QEMU
není podporováno; na Windows provádějte příkazy uvnitř Ubuntu WSL.
Varianta systému, kořenový oddíl a paměť VM jsou zaznamenané v `config/image.json`;
balíček obsahuje přehled kláves odpovídající této variantě.

## Příprava

Na Ubuntu nainstalujte hostitelské závislosti:

```bash
sudo apt-get update
sudo apt-get install qemu-system-arm qemu-system-gui qemu-utils python3 python3-tk python3-pil python3-pil.imagetk libpulse0 libpulse-mainloop-glib0
```

Je potřeba funkční GTK/OpenGL a PulseAudio. WSLg je obvykle poskytuje automaticky;
na běžném Linuxu použijte grafickou desktopovou relaci s PulseAudio nebo
kompatibilní službou PipeWire. Doporučené umístění balíčku je Linuxový filesystem
ve WSL, například `~/qemu-release`. Adresář musí být zapisovatelný.

Před prvním použitím lze ověřit kompletnost vydaného balíčku:

```bash
sha256sum -c SHA256SUMS
```

## Použití

```bash
bash start.sh
bash controls.sh       # znovu otevře přehled kláves
bash stop.sh           # řádně vypne systém a zavře přehled kláves
```

EmulationStation se načte automaticky, první boot může trvat několik minut.
Nápověda G350 obsahuje fotografii konzole s popisky tlačítek; jejich mapování
se mění podle vybraného profilu EmulationStation, RetroArch nebo 351Files.
Klávesy posílejte do okna QEMU. Tkinter okno je přehled ovládání, ve kterém lze
ručně přepínat profily; jeho zavření nechá VM běžet. Chybějící Tkinter nebrání
spuštění VM. Skripty lze volat i z jiného pracovního adresáře.

```bash
bash start.sh --no-controls
QEMU_AUDIO=none bash start.sh   # bez zvukových zařízení; nastavte před startem
```

Pro změnu režimu zvuku VM nejprve vypněte. Zvuk standardně používá HDA a
PulseAudio (`QEMU_AUDIO=auto` nebo `pa`). Bez dostupné služby PulseAudio použijte
`none`. SSH ani žádný síťový port hostitele se neotevírá.

Vypínejte přes `stop.sh` nebo vypnutí systému v ES. Zavření okna QEMU může
ukončit emulátor bez řádného vypnutí hostovaného systému. Pokud vypnutí přes
skript selže nebo překročí timeout, VM zůstane běžet pro diagnostiku.
Po opuštění ES přes F4 zůstane VM zapnutá; pro návrat do ES ji vypněte a spusťte.

## Ukázková hra SDLPoP

Pokud image obsahuje PortMaster, otevřete v ES **Ports -> PortMaster**. Při
prvním spuštění se nainstaluje připravený ukázkový port SDLPoP. PortMaster
ukončete a restartujte ES, aby se aktualizoval seznam her; poté zvolte
**Ports -> SDLPoP**. Ovládání a podrobnosti najdete v [PORTMASTER.md](PORTMASTER.md).

Stejný ZIP vytvořený vývojovým workflow je určen i k instalaci přes PortMaster
na fyzickém dArkOS. Uživatel ověřil hraní, zvuk a ovládání na dArkOS s podobným
výchozím obrazem, z jakého vychází QEMU. Ukládání a načítání pozice netestoval.
Jde o ukázku přenositelnosti mezi příbuznými prostředími dArkOS, nikoli ověření
všech modelů handheldů nebo dalších her z katalogu.

## Data, původ a diagnostika

Nastavení a uložené hry se zapisují přímo do `darkos.qcow2`. Pro čistý návrat
obnovte image z původního vydání. Zálohujte jej pouze při vypnuté VM.
Kontrolní součet disku v `SHA256SUMS` platí pro okamžik vydání; po prvním
použití se disk změní. Nespouštějte stejný image současně ve více VM.

Log QEMU a sériové konzole: `.runtime/logs/qemu.log`.
Log okna kláves: `.runtime/logs/workflow/controls.log`.
Stav a zámky: `.runtime/state/`. Tyto soubory nejsou součástí vydaných dat.
Balíček přemisťujte pouze při vypnuté VM.

Pokud se aplikace objeví jen na hlavním panelu s názvem `[WARN:COPY MODE]`, ale
okna jsou neviditelná nebo průhledná, může jít o známou chybu sdílené paměti WSLg:
[microsoft/wslg #1456](https://github.com/microsoft/wslg/issues/1456).
Spouštěč tuto kombinaci chyb v logu rozpozná před startem VM. Po zavření
grafických WSL aplikací lze ve Windows PowerShellu obnovit jen compositor:

```powershell
wsl.exe -d Ubuntu --system -- pkill -TERM -x weston
```

Před tím běžící VM vypněte pomocí `bash stop.sh`. Příkaz ukončí grafické
WSL aplikace; Weston se automaticky znovu spustí. Nemění image ani nevypíná
celé WSL. Pokud používáte jiný název distribuce, nahraďte `Ubuntu`.

`provenance.json` uvádí původní dArkOS image, dostupné kontrolní součty,
upstream release, kernel a revizi použitých receptů včetně necommitnutých změn.
Nedostupné údaje jsou výslovně označeny. Licenční informace jsou v `LICENSES.txt`
a uvnitř image v `/usr/share/doc`.
