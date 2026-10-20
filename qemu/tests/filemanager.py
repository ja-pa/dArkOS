"""Local QMP gate: ES Options -> 351Files keyboard -> same ES process."""
import hashlib,json,os,subprocess as sp,sys,time
from pathlib import Path
from PIL import Image
from workflow_qmp import QMP
Q=Path(__file__).resolve().parents[1];W=Path(os.environ['WORK_DIR']);logs=W/'logs/351files';logs.mkdir(parents=True,exist_ok=True)
qmp=QMP(os.environ.get('QMP_SOCKET',str(W/'state/qmp.sock')))
result={'passed':False,'runtime_id':(W/'state/runtime-id').read_text().strip(),'image_fingerprint':json.loads((W/'state/image.json').read_text())['fingerprint'],'checks':[]}
def remote(c):return sp.check_output(['bash',str(Q/'scripts/graphics-ssh.sh'),c],timeout=30)
def wait(c,timeout=90):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  p=sp.run(['bash',str(Q/'scripts/graphics-ssh.sh'),c],capture_output=True,timeout=30)
  if p.returncode==0:return p.stdout.decode().strip()
  time.sleep(.5)
 raise RuntimeError('Timed out: '+c)
def key(k,hold=150):
 qmp.command('send-key',{'keys':[{'type':'qcode','data':k}],'hold-time':hold});time.sleep(hold/1000+.5)
def request():remote('sudo -n mkdir -p /run/darkos-qemu; sudo -n rm -f /run/darkos-qemu/frame.ppm; sudo -n touch /run/darkos-qemu/capture.request')
def frame(name):
 wait('test -s /run/darkos-qemu/frame.ppm && test ! -e /run/darkos-qemu/capture.request')
 p=logs/(name+'.ppm');p.write_bytes(remote('sudo -n cat /run/darkos-qemu/frame.ppm'))
 im=Image.open(p).convert('RGB');im.save(p.with_suffix('.png'))
 if len(im.getcolors(im.width*im.height))<2:raise RuntimeError('Blank frame: '+name)
 return im

def opened_frame(name):
 # Wait for the child before requesting its frame: ES can otherwise consume
 # a request during the launch transition. Redraw without changing position.
 wait('pidof 351Files');time.sleep(3)
 key('down');request();key('up')
 return frame(name)

def changed(before,after):
 if before.tobytes()==after.tobytes():raise RuntimeError('Keyboard action did not change the rendered frame')

console=(logs/'es-console.log').open('w')
app=None
try:
 remote('! pidof emulationstation retroarch 351Files >/dev/null')
 app=sp.Popen(['bash',str(Q/'scripts/graphics-ssh.sh'),'cd /opt/darkos-es && sudo -n env DARKOS_QEMU_CAPTURE=1 bash /opt/darkos-qemu/env.sh ./emulationstation --home /home/ark --debug --no-splash'],stdout=console,stderr=sp.STDOUT)
 es=wait('pidof emulationstation');time.sleep(6)
 key('spc');time.sleep(1)
 # Six-system profile has no alternate-emulator entry: Options is sixth.
 for _ in range(5):key('down')
 key('ret');time.sleep(1);key('down')
 key('ret');initial=opened_frame('opened')
 command=remote('tr "\\0" " " < /proc/$(pidof 351Files)/cmdline').decode()
 if '/opt/darkos-qemu/351Files' not in command:raise RuntimeError('Original hardware-only 351Files was launched')
 expected_binary=hashlib.sha256((W/'artifacts/351files/351files').read_bytes()).hexdigest()
 if remote('sha256sum /opt/darkos-qemu/351Files').decode().split()[0]!=expected_binary:raise RuntimeError('Runtime 351Files differs from its build artifact')
 maps=remote('sudo -n cat /proc/$(pidof 351Files)/maps').decode();(logs/'351files.maps').write_text(maps)
 if 'libmali' in maps.lower() or '/opt/darkos-graphics/' not in maps:raise RuntimeError('Wrong 351Files graphics libraries')
 request();key('down');moved=frame('moved');changed(initial,moved)
 request();key('ret');opened=frame('directory')
 if initial.crop((0,0,640,32)).tobytes()==opened.crop((0,0,640,32)).tobytes():raise RuntimeError('Enter did not open a directory')
 request();key('backspace');back=frame('parent')
 if initial.crop((0,0,640,32)).tobytes()!=back.crop((0,0,640,32)).tobytes():raise RuntimeError('Backspace did not return to the parent directory')
 result['checks']+=['arrows','enter-directory','backspace-parent']
 request();key('pgdn');page=frame('page-down');changed(back,page)
 request();key('pgup');frame('page-up');result['checks'].append('page-up-down')
 request();key('insert');selected=frame('selected');key('up');request();key('insert');unselected=frame('unselected');changed(selected,unselected);result['checks'].append('selection')
 request();key('x');context=frame('context');changed(unselected,context)
 request();key('backspace');cancelled=frame('context-cancelled');changed(context,cancelled);result['checks'].append('context-backspace')
 key('esc');wait('! pidof 351Files >/dev/null');time.sleep(3);request();frame('es-returned')
 if wait('pidof emulationstation')!=es:raise RuntimeError('ES restarted')
 result['checks'].append('escape-main-return')
 key('ret');opened_frame('reopened')
 request();key('x');frame('second-context');key('esc');wait('! pidof 351Files >/dev/null');time.sleep(3);request();frame('es-dialog-returned')
 if wait('pidof emulationstation')!=es:raise RuntimeError('ES restarted after dialog exit')
 result['checks'].append('escape-dialog-return')
 key('ret');opened_frame('third-open');key('f4');wait('! pidof 351Files >/dev/null');time.sleep(3);request();frame('es-f4-returned')
 if wait('pidof emulationstation')!=es:raise RuntimeError('ES restarted after F4')
 result['checks'].append('f4-return')
 # Exit Options, then quit ES through its normal keyboard shortcut.
 key('esc');key('f4');wait('! pidof emulationstation >/dev/null');app.wait(timeout=30)
 result.update(passed=True,es_pid=es,binary_sha256=expected_binary)
finally:
 console.close()
 (W/'logs/351files-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
