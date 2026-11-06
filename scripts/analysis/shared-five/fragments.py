import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json,re
from pathlib import Path
ROOT=(_PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs');sys.path.insert(0,str(ROOT/'Transync测试/analysis_20261102/deps'))
import cv2,numpy as np
from rapidocr_onnxruntime import RapidOCR
cv2.setNumThreads(1);e=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,rec_batch_num=1,use_cls=False,det_limit_type='max',det_limit_side_len=780)
out=ROOT/'Parley测试/评测结果_20261103';vs={v['id']:v for v in json.loads((out/'manifest.json').read_text(encoding='utf-8'))};results=[]
for label,vid,lo,hi,mode in [('N01','V01',11.8,12.,'empty'),('N02','V01',36,37.533,'append'),('W01','V02',13,13.267,'empty'),('W02','V02',50,51.967,'append')]:
 cap=cv2.VideoCapture(str(ROOT/'Parley测试'/vs[vid]['path']));cache={}
 def get(n):
  cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,im=cap.read();assert ok
  return im[230:600,310:1100]
 def pred(n):
  if n not in cache:
   rr,_=e(get(n));words=[x[1] for x in (rr or []) if re.search('[A-Za-z]',x[1]) and not re.search('[\u4e00-\u9fff]',x[1]) and x[1].strip().lower() not in ['zh']];cache[n]=' '.join(words).lower()
  txt=cache[n]
  return bool(txt) if mode=='empty' else bool(re.search(r'friday\W*[a-z]{2,}',txt))
 a=round(lo*30);b=round(hi*30)
 if pred(a) or not pred(b):print('FAILED',label,cache,flush=True);continue
 while b-a>1:
  mid=(a+b)//2
  if pred(mid):b=mid
  else:a=mid
 paths=[]
 for n in [a,b]:
  p=out/'frames'/f'{label}_fragment_{n:05d}.png';cv2.imencode('.png',get(n))[1].tofile(str(p));paths.append(str(p.relative_to(out)))
 r={'scene':label,'last_absent_frame':a,'first_present_frame':b,'subtitle_pts_s':b/30,'boundary_screenshots':paths,'trace':cache};results.append(r);print(json.dumps(r,ensure_ascii=False),flush=True);cap.release()
(out/'subtitle_fragments.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
