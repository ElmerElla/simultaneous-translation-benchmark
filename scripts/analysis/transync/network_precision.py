import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json
from pathlib import Path
BASE=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102'));sys.path.insert(0,str(BASE/'deps'))
import cv2
from rapidocr_onnxruntime import RapidOCR
ocr=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)
cap=cv2.VideoCapture(str(BASE.parent/'outputs'/'延迟100ms、中断10s测试.mkv'))
rows=[]
def read(n):
    cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,f=cap.read();assert ok
    r,_=ocr(f[645:710,960:]);t=' '.join(v[1] for v in r) if r else ''
    rows.append({'frame':n,'pts':n/30,'text':t});return '连接中断' in t
events=[]
for label,lo,hi,want in [('interruption_on',54,55,True),('interruption_off',65,66,False),('delay_on',11,12,True)]:
    if label=='delay_on':break
    a=round(lo*30);b=round(hi*30);assert read(a)!=want and read(b)==want,(label,rows[-2:])
    while b-a>1:
        m=(a+b)//2
        if read(m)==want:b=m
        else:a=m
    events.append({'id':label,'before_frame':a,'after_frame':b,'before_pts':a/30,'after_pts':b/30})
    for n in [a,b]:
        cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,f=cap.read();cv2.imencode('.png',f)[1].tofile(str(BASE/'frames'/f'{label}_{n}.png'))
for sec in [74,75,76,78,79,80,82,84]:
    n=sec*30;cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,f=cap.read();cv2.imencode('.png',f)[1].tofile(str(BASE/'frames'/f'network_detail_{sec}.png'))
cap.release()
(BASE/'network_events.json').write_text(json.dumps({'events':events,'traces':rows},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(events),flush=True)
