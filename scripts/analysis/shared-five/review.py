import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json,argparse
from pathlib import Path
ROOT=(_PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs')
sys.path.insert(0,str(ROOT/'Transync测试/analysis_20261102/deps'))
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('product');p.add_argument('video');p.add_argument('--times');p.add_argument('--step',type=float,default=5);p.add_argument('--rect',default='0,0,1920,1080');p.add_argument('--label',default='review');p.add_argument('--width',type=int,default=960);p.add_argument('--cols',type=int,default=2);p.add_argument('--batch',type=int,default=12)
a=p.parse_args();out=ROOT/a.product/'评测结果_20261103';vs=json.loads((out/'manifest.json').read_text(encoding='utf-8'));v=next(x for x in vs if x['id']==a.video)
times=[float(x) for x in a.times.split(',')] if a.times else list(np.arange(0,v['duration_s'],a.step))
rect=tuple(int(x) for x in a.rect.split(','));cap=cv2.VideoCapture(str(ROOT/a.product/v['path']));font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
ims=[]
for t in times:
 n=round(t*30);cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,img=cap.read()
 if not ok:continue
 x1,y1,x2,y2=rect;img=img[y1:y2,x1:x2]
 cv2.imencode('.png',img)[1].tofile(str(out/'frames'/f'{a.video}_{a.label}_{n:05d}.png'))
 im=Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB));im=im.resize((a.width,round(im.height*a.width/im.width)));ims.append((t,n,im))
cap.release()
for start in range(0,len(ims),a.batch):
 batch=ims[start:start+a.batch];h=batch[0][2].height+28
 canvas=Image.new('RGB',(a.width*a.cols,h*((len(batch)+a.cols-1)//a.cols)),'#dddddd');draw=ImageDraw.Draw(canvas)
 for i,(t,n,im) in enumerate(batch):
  x=(i%a.cols)*a.width;y=(i//a.cols)*h;draw.text((x+5,y+2),f'{a.product} {a.video} {t:.3f}s / frame {n}',font=font,fill='black');canvas.paste(im,(x,y+28))
 f=out/'frames'/f'{a.video}_{a.label}_contact_{start//a.batch+1}.jpg';canvas.save(f);print(f,flush=True)
