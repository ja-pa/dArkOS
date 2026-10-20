"""Optional host-side control legend; no guest connections or input injection."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

SCRIPT = Path(__file__).resolve()
CONFIG = SCRIPT.parents[1] / 'config/controls.json'


def window_pid(state, work):
    """Never signal an unrelated process when a PID file outlives its window."""
    try:
        saved = json.loads(state.read_text())
        proc = Path('/proc') / str(saved['pid'])
        args = (proc / 'cmdline').read_bytes().split(b'\0')
        started = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]
        if (started == saved['started'] and str(SCRIPT).encode() in args
                and b'show' in args and str(work).encode() in args):
            return saved['pid']
    except (OSError, ValueError, KeyError, IndexError):
        pass
    return None


def show(work, state):
    # The window itself holds the lock, including during Tk initialization.
    with (work / 'state/controls.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        import tkinter as tk
        from tkinter import ttk
        profiles = json.loads(CONFIG.read_text())['profiles']
        root = tk.Tk()
        root.title('dArkOS — Controls')
        root.geometry(f'{min(1120, root.winfo_screenwidth()-60)}x{min(920, root.winfo_screenheight()-90)}+40+40')
        root.minsize(980, 720)
        outer = ttk.Frame(root, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='G350 · Klávesnice v QEMU', font=('sans', 18, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='Tlačítko na konzoli → klávesa na počítači').pack(anchor='w', pady=(4, 8))
        profile = ttk.Combobox(outer, values=[p['name'] for p in profiles], state='readonly')
        profile.pack(fill='x', pady=(0, 10))
        body = ttk.Frame(outer)
        body.pack(fill='both', expand=True)
        canvas = tk.Canvas(body, name='diagram', background='white', highlightthickness=0)
        canvas.pack(side='left', fill='both', expand=True)
        side = ttk.Frame(body, padding=(16, 0, 0, 0))
        side.pack(side='right', fill='y')
        ttk.Label(side, text='Zkratky a navigace', font=('sans', 12, 'bold')).pack(anchor='w', pady=(4, 12))
        rows = ttk.Frame(side, name='rows')
        rows.pack(fill='x')
        note = ttk.Label(side, wraplength=255, justify='left')
        note.pack(fill='x', pady=(20, 0))
        ttk.Label(side, text='M a analogové páčky nemají\nv tomto profilu klávesové mapování.\n— = bez přiřazené klávesy',
                  wraplength=255, justify='left').pack(anchor='w', pady=(20, 0))
        ttk.Label(side, text='Toto okno pouze ukazuje nápovědu.\nKlávesy posílejte do okna QEMU.',
                  wraplength=255, justify='left').pack(anchor='w', pady=(20, 0))
        from PIL import Image, ImageTk
        photo = Image.open(CONFIG.parent / 'g350_picture.jpg').convert('RGB')
        # Crops are UI viewports of the original photograph; labels stay live canvas items.
        front = photo.crop((170, 240, 537, 812))
        rear = photo.crop((570, 380, 930, 505))
        canvas.images = []

        def draw(_event=None):
            if profile.current() < 0:
                return
            mapping = profiles[profile.current()]['diagram']
            canvas.delete('all')
            scale = min(max(1, canvas.winfo_width()) / 740, max(1, canvas.winfo_height()) / 730)
            ox = (canvas.winfo_width() - 740 * scale) / 2
            def xy(x, y): return ox+x*scale, y*scale
            def text(x, y, value, size=11, **kw):
                return canvas.create_text(*xy(x,y), text=value, font=('sans', max(8, round(size*scale)), 'bold'), **kw)
            def line(points, color='#64748b'):
                canvas.create_line(*[v for x,y in points for v in xy(x,y)], fill=color, width=max(1,2*scale))
            def image_at(source, x, y, width):
                im=ImageTk.PhotoImage(source.resize((max(1,round(width*scale)),max(1,round(source.height*width/source.width*scale))),Image.Resampling.LANCZOS))
                canvas.images.append(im)
                canvas.create_image(*xy(x,y),image=im,anchor='nw')
            canvas.images=[]
            image_at(front, 205, 16, 330)
            def target(x,y): return 205+(x-170)*330/367,16+(y-240)*330/367
            def callout(name, key, point, x,y):
                tx,ty=target(*point)
                edge=x+155 if x<200 else x
                line([(tx,ty),(edge, y+27)])
                radius=6*scale
                px,py=xy(tx,ty)
                canvas.create_oval(px-radius,py-radius,px+radius,py+radius,outline='#2563eb',width=max(1,2*scale))
                x1,y1=xy(x,y);x2,y2=xy(x+155,y+55)
                canvas.create_rectangle(x1,y1,x2,y2,fill='#f1f5f9',outline='#cbd5e1')
                text(x+10,y+15,name,10,anchor='w',fill='#475569')
                text(x+10,y+37,key,14,anchor='w',fill='#1d4ed8')
            callout('D-pad',mapping['dpad'],(255,600),10,275)
            callout('M','—',(355,563),10,175)
            callout('SELECT',mapping['select'],(325,655),10,420)
            for button,point,y in [('x',(454,563),175),('y',(418,600),245),('a',(490,600),315),('b',(454,635),385)]:
                callout(button.upper(),mapping[button],point,575,y)
            callout('START',mapping['start'],(385,655),575,465)
            text(370,554,'Analogové páčky: bez mapování',10,fill='#64748b')
            text(370,585,'Ramena · pohled zezadu',12,fill='#334155')
            image_at(rear, 220, 610, 280)
            # Rear view is mirrored: R1/R2 on the left, L2/L1 on the right.
            for button,x,tx in [('r',45,610),('r2',185,670),('l2',365,825),('l',535,885)]:
                key=mapping[button];label={'r':'R1','l':'L1','r2':'R2','l2':'L2'}[button]
                bx=220+(tx-570)*280/360
                line([(bx,656),(x+68,704)])
                text(x+68,718,label+' → '+key,11,fill='#1d4ed8')

        def select(_event=None):
            for child in rows.winfo_children():
                child.destroy()
            current = profiles[profile.current()]
            for row, (action, key) in enumerate(current['controls']):
                # Long descriptions wrap within the side panel instead of widening the diagram window.
                ttk.Label(rows, text=action, wraplength=160).grid(row=row, column=0, sticky='w', pady=6)
                ttk.Label(rows, text=key, font=('sans', 10, 'bold'), wraplength=90).grid(
                    row=row, column=1, sticky='e', padx=(10, 0), pady=6)
            note.configure(text=current['note'])
            draw()

        profile.bind('<<ComboboxSelected>>', select)
        canvas.bind('<Configure>', draw)
        profile.current(0)
        select()
        signal.signal(signal.SIGTERM, lambda *_: root.destroy())

        def tick():
            root.after(200, tick)  # Allow Python to deliver SIGTERM while idle in Tk.

        tick()
        pid = os.getpid()
        started = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
        state.write_text(json.dumps({'pid': pid, 'started': started}))
        try:
            root.mainloop()
        finally:
            state.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop', 'show'])
    parser.add_argument('work', type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    (work / 'state').mkdir(parents=True, exist_ok=True)
    state = work / 'state/controls.json'
    if args.action == 'show':
        show(work, state)
    elif args.action == 'stop':
        pid = window_pid(state, work)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            for _ in range(20):
                if not window_pid(state, work):
                    break
                time.sleep(0.1)
    else:
        if window_pid(state, work):
            return
        log = work / 'logs/workflow/controls.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open('ab') as output:
            child = subprocess.Popen([sys.executable, str(SCRIPT), 'show', str(work)],
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                     start_new_session=True)
        for _ in range(30):
            if window_pid(state, work):
                return
            if child.poll() is not None:
                break
            time.sleep(0.1)
        print(f'Warning: controls window unavailable; install python3-tk and check WSLg. Log: {log}',
              file=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Optional help must never prevent QEMU from starting.
        print(f'Warning: controls window: {error}', file=sys.stderr)
