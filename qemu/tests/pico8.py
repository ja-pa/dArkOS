"""QMP integration: original PICO-8 carts, keyboard, persistence and ES resume.
Run against a prepared development VM with WORK_DIR and SSH_PORT set.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import re
import subprocess as sp
import time
from helpers.workflow_qmp import QMP

Q = Path(__file__).resolve().parents[1]
W = Path(os.environ['WORK_DIR'])
logs = W/'logs/pico8'
logs.mkdir(parents=True, exist_ok=True)
qmp = QMP(os.environ.get('QMP_SOCKET', str(W/'state/qmp.sock')))

def remote(command, **kwargs):
    return sp.run(['bash',str(Q/'scripts/graphics-ssh.sh'),command],check=True,capture_output=True,**kwargs)

def text(command): return remote(command).stdout.decode().strip()

def wait(command, timeout=120):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        result=sp.run(['bash',str(Q/'scripts/graphics-ssh.sh'),command],capture_output=True)
        if result.returncode==0:return result.stdout.decode().strip()
        time.sleep(1)
    raise RuntimeError('Timed out: '+command)

def key(code, hold=150):
    qmp.command('send-key',{'keys':[{'type':'qcode','data':code}],'hold-time':hold})
    time.sleep(hold/1000+.7)

def screenshot(name):
    remote('sudo -n mkdir -p /run/darkos-qemu; sudo -n rm -f /run/darkos-qemu/frame.ppm; sudo -n touch /run/darkos-qemu/capture.request')
    wait('test -s /run/darkos-qemu/frame.ppm && test ! -e /run/darkos-qemu/capture.request',45)
    data=remote('sudo -n cat /run/darkos-qemu/frame.ppm').stdout
    (logs/(name+'.ppm')).write_bytes(data)
    from PIL import Image
    image=Image.open(logs/(name+'.ppm')).convert('RGB')
    assert len(image.getcolors(image.width*image.height))>2, 'Blank frame: '+name
    image.save(logs/(name+'.png'))
    return hashlib.sha256(image.tobytes()).hexdigest()

cart='/roms/pico-8/carts/000 QEMU Pico8 probe.p8'
probe="""pico-8 cartridge // http://www.pico-8.com
version 42
__lua__
function _init()
 cartdata("darkos_qemu_pico8_probe")
 n=dget(0)+1
 dset(0,n)
 x=20
 for i=0,31 do
  poke(0x3200+i*2,33)
  poke(0x3201+i*2,14)
 end
 poke(0x3241,8)
 poke(0x3242,0)
 poke(0x3243,32)
 sfx(0)
end
function _update()
 if btn(1) then x=min(110,x+1) end
 if btn(0) then x=max(0,x-1) end
 if btnp(4) then n=n+1 dset(0,n) end
end
function _draw()
 cls(1)
 print("qemu pico-8 probe",8,8,7)
 print("save counter: "..n,8,20,10)
 rectfill(x,60,x+8,68,8)
end
"""
original=text('sudo -n cat /home/ark/.emulationstation/es_settings.cfg')
result={'passed':False,'original_core':True,'games':{},'limitations':['No physical gamepad test; host speaker playback must be checked separately.']}
app=None
try:
    core='/home/ark/.config/retroarch/cores/fake08_libretro.so'
    expected=json.loads((W/'logs/inspect/files.json').read_text())[core]['sha256']
    actual=text('sha256sum '+core).split()[0]
    assert actual==expected, 'FAKE-08 differs from the original release core'
    result['core_sha256']=actual
    remote('! pidof emulationstation retroarch >/dev/null; test -f /home/ark/.config/retroarch/cores/fake08_libretro.so; test ! -e '+shlex.quote(cart))
    remote('sudo -n tee '+shlex.quote(cart)+' >/dev/null',input=probe.encode())
    code=r"""from pathlib import Path
import re,xml.etree.ElementTree as E
p=Path('/home/ark/.emulationstation/es_settings.cfg')
t=E.fromstring('<settings>'+re.sub(r'<\?xml.*?\?>','',p.read_text())+'</settings>')
for tag,name,value in [('string','StartupSystem','pico-8'),('bool','StartupOnGameList','true')]:
 for item in list(t):
  if item.get('name')==name:t.remove(item)
 E.SubElement(t,tag,name=name,value=value)
p.write_text('<?xml version="1.0"?>'+chr(10)+chr(10).join(E.tostring(x,encoding='unicode') for x in t))
"""
    remote('sudo -n python3 -',input=code.encode())
    log=(logs/'es-console.log').open('wb')
    app=sp.Popen(['bash',str(Q/'scripts/graphics-ssh.sh'),'cd /opt/darkos-es && sudo -n env DARKOS_QEMU_CAPTURE=1 bash /opt/darkos-qemu/env.sh ./emulationstation --home /home/ark --debug --no-splash'],stdout=log,stderr=sp.STDOUT)
    es=wait('pidof emulationstation');time.sleep(8)
    screenshot('menu')
    # First run: deterministic movement and persistent state from a text cart.
    probe_frames=[]
    for index in range(2):
        key('ret');pid=wait('pidof retroarch');time.sleep(5)
        args=text('sudo -n cat /proc/'+pid+'/cmdline').replace(chr(0),' ')
        assert cart in args and 'fake08_libretro.so' in args, args
        before=screenshot('probe-'+str(index))
        probe_frames.append(before)
        key('right',1200)
        after=screenshot('probe-moved-'+str(index))
        assert before!=after, 'Keyboard did not move the probe'
        key('f2')
        saved=wait("grep 'Saving state' /home/ark/.config/retroarch/logs/last-run.log | grep -v RAM | tail -1 | grep .")
        state=re.search(r'Saving state \"([^\"]+)\"',saved).group(1)
        wait('test -s '+shlex.quote(state))
        key('f4');time.sleep(2)
        corelog=text('sudo -n cat /home/ark/.config/retroarch/logs/last-run.log')
        assert 'loading state' in corelog.lower() or 'loaded state' in corelog.lower(),corelog[-1000:]
        (logs/('probe-'+str(index)+'.log')).write_text(corelog)
        key('esc',1000);wait('! pidof retroarch >/dev/null');time.sleep(3)
        assert text('pidof emulationstation')==es
    assert probe_frames[0]!=probe_frames[1], 'Persistent counter did not survive restart'
    result['probe']={'persistent_cartdata':True,'text_cart_with_spaces':True,'keyboard_movement':True,'save_load_state':True,'es_pid':es}
    # Enumerate the shipped PNG carts in the menu after the temporary first entry.
    carts=text("find /roms/pico-8/carts -maxdepth 1 -type f -iname '*.png' | sort -f").splitlines()
    for index,path in enumerate(carts):
        key('down');key('ret');pid=wait('pidof retroarch');time.sleep(7)
        args=text('sudo -n cat /proc/'+pid+'/cmdline').replace(chr(0),' ')
        assert path in args,args
        maps=text('sudo -n cat /proc/'+pid+'/maps')
        (logs/('cart-'+str(index)+'.maps')).write_text(maps)
        assert 'fake08_libretro.so' in maps
        assert not any(v in maps.lower() for v in ['libmali','librga','libgo2'])
        key('z');key('ret');time.sleep(2)
        screenshot('cart-'+str(index))
        (logs/('cart-'+str(index)+'.log')).write_bytes(remote('sudo -n cat /home/ark/.config/retroarch/logs/last-run.log').stdout)
        key('esc',1000);wait('! pidof retroarch >/dev/null');time.sleep(3)
        assert text('pidof emulationstation')==es
        result['games'][Path(path).name]={'launched':True,'returned_to_same_es':True}
    result['passed']=True
finally:
    remote('sudo -n tee /home/ark/.emulationstation/es_settings.cfg >/dev/null',input=original.encode())
    if text('pidof retroarch || true'):key('esc',1000);wait('! pidof retroarch >/dev/null')
    if text('pidof emulationstation || true'):key('f4');wait('! pidof emulationstation >/dev/null')
    remote('sudo -n rm -f -- '+shlex.quote(cart)+' '+shlex.quote(cart[:-3]+'.state')+' /roms/pico-8/carts/cdata/darkos_qemu_pico8_probe.p8d.txt')
    (logs/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    if app:app.wait(timeout=30)
print(json.dumps(result,indent=2))
