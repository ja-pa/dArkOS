"""Local GTK/WSLg integration gate using QMP keyboard events and original cores."""
import hashlib,json,os,shlex,subprocess as sp,sys,time,re
from pathlib import Path
from workflow_qmp import QMP
from PIL import Image
Q=Path(__file__).resolve().parents[1]; W=Path(os.environ['WORK_DIR']); logs=W/'logs/integration';logs.mkdir(exist_ok=True,parents=True)
qmp=QMP(os.environ.get('QMP_SOCKET',str(W/'state/qmp.sock')))
results={'runtime_id':(W/'state/runtime-id').read_text().strip(),'image_fingerprint':json.loads((W/'state/image.json').read_text())['fingerprint'],'passed':False,'systems':{},'limitations':['Audio not validated by this graphics test; no physical gamepad; no timing/playability claim']}
def remote(command,**kwargs):
    return sp.run(['bash',str(Q/'scripts/graphics-ssh.sh'),command],check=True,text=True,capture_output=True,**kwargs).stdout.strip()
def wait(command,timeout=120):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        p=sp.run(['bash',str(Q/'scripts/graphics-ssh.sh'),command],text=True,capture_output=True)
        if p.returncode==0:return p.stdout.strip()
        time.sleep(1)
    raise RuntimeError('Timed out: '+command)
def key(code):
    qmp.command('send-key',{'keys':[{'type':'qcode','data':code}],'hold-time':150});time.sleep(.6)
def screenshot(name):
    p=logs/(name+'.ppm'); deadline=time.monotonic()+30
    while True:
        remote('sudo -n mkdir -p /run/darkos-qemu; sudo -n rm -f /run/darkos-qemu/frame.ppm; sudo -n touch /run/darkos-qemu/capture.request')
        wait('test -s /run/darkos-qemu/frame.ppm && test ! -e /run/darkos-qemu/capture.request')
        captured=sp.run(['bash',str(Q/'scripts/graphics-ssh.sh'),'sudo -n cat /run/darkos-qemu/frame.ppm'],check=True,capture_output=True).stdout
        p.write_bytes(captured); im=Image.open(p).convert('RGB')
        if len(im.getcolors(im.width*im.height))>=2:
            im.save(p.with_suffix('.png'))
            return hashlib.sha256(im.tobytes()).hexdigest()
        # Window recreation can present a clear frame before the theme appears.
        if time.monotonic()>=deadline:raise RuntimeError('Blank/near-blank screen: '+name)
        time.sleep(1)
def configure_start(system):
    code=r"""from pathlib import Path
import xml.etree.ElementTree as E
import re
p=Path('/home/ark/.emulationstation/es_settings.cfg'); text=re.sub(r'<\?xml.*?\?>','',p.read_text());t=E.fromstring('<settings>'+text+'</settings>')
for tag,name,value in [('string','StartupSystem',SYSTEM),('bool','StartupOnGameList','true')]:
 for old in list(t):
  if old.get('name')==name:t.remove(old)
 E.SubElement(t,tag,name=name,value=value)
p.write_text('<?xml version="1.0"?>'+chr(10)+chr(10).join(E.tostring(x,encoding='unicode') for x in t))
""".replace('SYSTEM',repr(system))
    # Pass Python as stdin, avoiding shell interpolation of profile data.
    sp.run(['bash',str(Q/'scripts/graphics-ssh.sh'),'sudo -n python3 -'],input=code,text=True,check=True,capture_output=True)
original_settings=remote('sudo -n cat /home/ark/.emulationstation/es_settings.cfg')
(logs/'es-settings.before-test.cfg').write_text(original_settings)
(W/'logs/test-results.json').write_text(json.dumps(results,indent=2)+'\n')
try:
    remote('test "$(dpkg --print-architecture)" = arm64; test -e /dev/dri/card0; test -e /dev/input/event0; ! pidof emulationstation retroarch >/dev/null')
    for system in ['gb','gbc','nes','snes','gba','megadrive']:
        configure_start(system)
        f=(logs/(system+'-es-console.log')).open('w')
        app=sp.Popen(['bash',str(Q/'scripts/graphics-ssh.sh'),'cd /opt/darkos-es && sudo -n env DARKOS_QEMU_CAPTURE=1 bash /opt/darkos-qemu/env.sh ./emulationstation --home /home/ark --debug --no-splash'],stdout=f,stderr=sp.STDOUT)
        try:
            pid=wait('pidof emulationstation');time.sleep(6)
            before=screenshot(system+'-es')
            key('ret')
            ra=wait('pidof retroarch');time.sleep(8)
            # Confirm the ES process launched exactly the selected original core.
            cmd=remote('tr "\\0" " " < /proc/'+ra+'/cmdline')
            core={'gb':'gambatte','gbc':'gambatte','nes':'fceumm','snes':'snes9x','gba':'mgba','megadrive':'genesis_plus_gx'}[system]
            if core+'_libretro.so' not in cmd: raise RuntimeError('Unexpected core: '+cmd)
            maps=remote('sudo -n cat /proc/'+ra+'/maps');(logs/(system+'-retroarch.maps')).write_text(maps)
            if any(v in maps.lower() for v in ['libmali','librga','libgo2']):raise RuntimeError('Vendor runtime library loaded')
            game=screenshot(system+'-game')
            if before==game: raise RuntimeError('Game did not replace ES screen')
            key('f2')
            saved=wait("sudo -n grep 'Saving state' /home/ark/.config/retroarch/logs/last-run.log | grep -v 'RAM' | tail -1 | grep .")
            match=re.search(r'Saving state "([^"]+)"',saved)
            if not match: raise RuntimeError('Missing saved-state pathname')
            state=match.group(1)
            wait('sudo -n test -s '+shlex.quote(state))
            key('ret');key('z');time.sleep(2)
            key('f4');time.sleep(2)
            lastlog=remote('sudo -n cat /home/ark/.config/retroarch/logs/last-run.log');(logs/(system+'-retroarch.log')).write_text(lastlog)
            if 'loading state' not in lastlog.lower() and 'loaded state' not in lastlog.lower():raise RuntimeError('No load-state confirmation in RetroArch log')
            if 'saving state' not in lastlog.lower() and 'saved state' not in lastlog.lower():raise RuntimeError('No save-state confirmation in RetroArch log')
            key('esc');wait('! pidof retroarch >/dev/null');time.sleep(4)
            returned=screenshot(system+'-returned')
            if remote('pidof emulationstation')!=pid:raise RuntimeError('ES was restarted instead of resuming')
            esmaps=remote('sudo -n cat /proc/'+pid+'/maps');(logs/(system+'-es.maps')).write_text(esmaps)
            for library in ['libSDL2','libEGL','libOpenGL','libgbm','libgallium']:
                if not any('/opt/darkos-graphics/usr/lib/aarch64-linux-gnu/' in line and library in line for line in esmaps.splitlines()):raise RuntimeError('Missing private ES runtime library '+library)
            if any(v in esmaps.lower() for v in ['libmali','librga','libgo2']):raise RuntimeError('Vendor ES runtime library loaded')
            results['systems'][system]={'passed':True,'core':core,'state':state,'es_pid':pid,'screenshots':[system+'-es.png',system+'-game.png',system+'-returned.png']}
            key('f4');wait('! pidof emulationstation >/dev/null');app.wait(timeout=30)
        finally:
            f.close()
    results['passed']=True
finally:
    # Restore startup selection on failure as well as success.
    sp.run(['bash',str(Q/'scripts/graphics-ssh.sh'),'sudo -n tee /home/ark/.emulationstation/es_settings.cfg >/dev/null'],input=original_settings,text=True,check=True,capture_output=True)
    (W/'logs/test-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
