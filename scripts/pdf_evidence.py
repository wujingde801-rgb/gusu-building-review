#!/usr/bin/env python3
"""Render a source-PDF crop and register it without claiming visual review."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image
import review

def capture(state_path,page,bbox,observation,quality='unclear',poppler=None):
    state_path=Path(state_path).resolve(); state=review.read(state_path)
    source=state['source']
    if review.hashfile(source['path'])!=source['sha256']: raise ValueError('PDF已变化')
    if page not in range(1,source['pages']+1): raise ValueError('非法PDF页码')
    if len(bbox)!=4 or not all(0<=v<=1 for v in bbox) or bbox[0]>=bbox[2] or bbox[1]>=bbox[3]: raise ValueError('bbox须0..1且有正面积')
    exe=poppler or shutil.which('pdftoppm')
    if not exe: raise ValueError('缺少pdftoppm；请使用WorkBuddy运行时路径，或原生PDF工具登记截图')
    target=state_path.parent/'evidence'; target.mkdir(exist_ok=True)
    import uuid
    eid='E-'+uuid.uuid4().hex[:12]; output=target/(eid+'.png')
    with tempfile.TemporaryDirectory() as tmp:
        stem=Path(tmp)/'page'
        subprocess.run([exe,'-f',str(page),'-l',str(page),'-singlefile','-scale-to','2400','-png',source['path'],str(stem)],check=True,timeout=60,capture_output=True)
        with Image.open(str(stem)+'.png') as im:
            w,h=im.size
            im.crop((int(bbox[0]*w),int(bbox[1]*h),int(bbox[2]*w),int(bbox[3]*h))).save(output)
    item={'id':eid,'source_sha256':source['sha256'],'page':page,'bbox':bbox,'path':str(output),
          'sha256':review.hashfile(output),'observation':observation,'quality':quality}
    state['evidence'].append(item); review.write(state_path,state)
    return item

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('state'); p.add_argument('--page',type=int,required=True); p.add_argument('--bbox',type=float,nargs=4,default=[0,0,1,1]); p.add_argument('--observation',required=True); p.add_argument('--quality',choices=['clear','unclear'],default='unclear'); p.add_argument('--poppler'); a=p.parse_args()
    print(review.kb.dump(capture(a.state,a.page,a.bbox,a.observation,a.quality,a.poppler)))
if __name__=='__main__': main()
