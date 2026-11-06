import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json
from pathlib import Path
BASE=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102'));sys.path.insert(0,str(BASE/'deps'))
import cv2
from PIL import Image,ImageDraw
videos={'normal':'冷启动、正常翻译、关闭音色克隆翻译.mkv','network':'延迟100ms、中断10s测试.mkv'}
def contact(key,times,crop,label,width=960,cols=2):
    cap=cv2.VideoCapture(str(BASE.parent/'outputs'/videos[key]));imgs=[]
    for t in times:
        cap.set(cv2.CAP_PROP_POS_FRAMES,round(t*30));ok,f=cap.read()
        if not ok:continue
        im=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB));im.save(BASE/'frames'/f'{key}_{round(t*30):05d}.png')
        im=im.crop(crop);im=im.resize((width,round(im.height*width/im.width)))
        imgs.append((t,im))
    cap.release();height=imgs[0][1].height+26
    canvas=Image.new('RGB',(width*cols,height*((len(imgs)+cols-1)//cols)),'#dddddd');draw=ImageDraw.Draw(canvas)
    for i,(t,im) in enumerate(imgs):
        x=i%cols*width;y=i//cols*height;canvas.paste(im,(x,y+26));draw.text((x+10,y+5),f'{key} t={t:.3f}s frame={round(t*30)}',fill='black')
    canvas.save(BASE/'frames'/f'{label}.jpg')
contact('normal',[8,9,10,11,12,12.5,13,13.5,14,14.5],(0,0,1500,260),'startup',750)
contact('normal',[87,88,89,90,91,92],(0,0,960,700),'clone_setting',800)
contact('network',[12,14,44,54,55,59,63,64,65,68],(960,560,1920,900),'network_controls',960)
