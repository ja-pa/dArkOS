"""Content inventory without following guest symlinks; also used for delta manifests."""
import hashlib,json,os,sys
from pathlib import Path

def inventory(root):
    root=Path(root); result={}
    for base,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if str((Path(base)/d).relative_to(root)) not in ['dev','proc','sys','run'])
        for name in sorted(dirs+files):
            p=Path(base)/name; rel='/'+str(p.relative_to(root)); s=p.lstat()
            item={'mode':oct(s.st_mode & 0o7777),'uid':s.st_uid,'gid':s.st_gid}
            if p.is_symlink(): item['symlink']=os.readlink(p)
            elif p.is_file():
                h=hashlib.sha256()
                with p.open('rb') as f:
                    while b:=f.read(4*1024*1024): h.update(b)
                item['sha256']=h.hexdigest(); item['size']=s.st_size
            else: continue
            result[rel]=item
    return result

if __name__=='__main__':
    Path(sys.argv[2]).write_text(json.dumps(inventory(sys.argv[1]),sort_keys=True,indent=2)+'\n')
