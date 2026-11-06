import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json
from pathlib import Path
BASE=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102'));sys.path.insert(0,str(BASE/'deps'))
import numpy as np,cv2
from rapidocr_onnxruntime import RapidOCR
engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)
names={'normal':'冷启动、正常翻译、关闭音色克隆翻译.mkv','network':'延迟100ms、中断10s测试.mkv'}
traces=[];results=[]
def frame(cap,n):
    cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,img=cap.read();assert ok
    return img
for key,label,lo,hi in [('normal','cold_subtitle',19,20),('normal','warm_subtitle',64,65),('normal','default_subtitle',101,102),('network','delay_subtitle',22,23)]:
    cap=cv2.VideoCapture(str(BASE.parent/'outputs'/names[key]))
    def pred(n):
        img=frame(cap,n);r,_=engine(img[270:610,:950]);text=' '.join(x[1] for x in r) if r else ''
        ok='please' in text.lower() or 'confirm' in text.lower()
        traces.append({'label':label,'frame':n,'pts':n/30,'text':text,'matched':ok});return ok
    a=round(lo*30);b=round(hi*30);assert not pred(a) and pred(b),(label,a,b)
    while b-a>1:
        mid=(a+b)//2
        if pred(mid):b=mid
        else:a=mid
    before=frame(cap,a);after=frame(cap,b)
    for n,img in [(a,before),(b,after)]:cv2.imencode('.png',img)[1].tofile(str(BASE/'frames'/f'{label}_{n}.png'))
    results.append({'id':label,'key':key,'last_absent_frame':a,'first_present_frame':b,'last_absent_pts':a/30,'first_present_pts':b/30})
    cap.release();print(label,results[-1],flush=True)
cap=cv2.VideoCapture(str(BASE.parent/'outputs'/names['normal']))
states=[]
for n in range(380,442):
    img=frame(cap,n);icon=img[153:177,215:241]
    green=int(np.sum((icon[:,:,1].astype(int)>icon[:,:,2].astype(int)+25)&(icon[:,:,1].astype(int)>icon[:,:,0].astype(int)+25)))
    black=int(np.sum(np.max(icon,axis=2)<65))
    states.append({'frame':n,'pts':n/30,'green':green,'black':black})
cap.release()
(BASE/'precise_events.json').write_text(json.dumps({'subtitle_events':results,'ocr_boundary_traces':traces,'startup_icon_states':states},ensure_ascii=False,indent=2),encoding='utf-8')
print(states,flush=True)
