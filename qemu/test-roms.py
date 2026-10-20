"""Fetch pinned free 240p/144p/160p suites; never substitute arbitrary ROMs."""
import hashlib,http.cookiejar,json,os,re,urllib.parse,urllib.request,zipfile,io
from pathlib import Path
q=Path(__file__).parent; out=Path(os.environ['WORK_DIR'])/'test-roms';out.mkdir(exist_ok=True)
roms=json.loads((q/'test-roms.json').read_text())
opener=None; download_page=None; token=None
for item in roms:
    dest=out/item['filename']
    if dest.exists():
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=item['sha256']: raise RuntimeError('Changed test ROM: '+str(dest))
        continue
    if 'itch_upload_id' not in item:
        data=urllib.request.urlopen(item['url'],timeout=30).read()
    else:
        archive=out/item['archive_filename']
        if archive.exists():
            zipped=archive.read_bytes()
        else:
            if opener is None:
                opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                base=item['url']; page=opener.open(base,timeout=30).read().decode()
                token=re.search(r'name="csrf_token" value="([^"]+)"',page)[1]
                def post(url,referer):
                    return urllib.request.Request(url,data=urllib.parse.urlencode({'csrf_token':token}).encode(),headers={'Referer':referer})
                result=json.load(opener.open(post(base+'/download_url',base),timeout=30));download_page=result['url']
                page=opener.open(download_page,timeout=30).read().decode();token=re.search(r'name="csrf_token" value="([^"]+)"',page)[1]
            response=json.load(opener.open(post(item['url']+'/file/'+item['itch_upload_id'],download_page),timeout=30))
            if 'url' not in response: raise RuntimeError('Free test suite download unavailable: '+str(response))
            zipped=opener.open(response['url'],timeout=60).read()
            if hashlib.sha256(zipped).hexdigest()!=item['archive_sha256']: raise RuntimeError('Test suite archive changed')
            archive.write_bytes(zipped)
        if hashlib.sha256(zipped).hexdigest()!=item['archive_sha256']: raise RuntimeError('Test suite archive checksum failure')
        data=zipfile.ZipFile(io.BytesIO(zipped)).read(item['archive_member'])
    if hashlib.sha256(data).hexdigest()!=item['sha256']: raise RuntimeError('Test ROM checksum failure')
    dest.write_bytes(data)
print('All five free test ROMs verified against qemu/test-roms.json')
