import os as _publication_os
from pathlib import Path as _PublicationPath
"""Frame-boundary candidates and acoustic onsets. Candidates require visual review."""
import sys,json,re
from pathlib import Path
ROOT=(_PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs');SHARED=ROOT/'Transync测试/analysis_20261102'
sys.path.insert(0,str(SHARED/'deps'))
import cv2,numpy as np,soundfile as sf
from rapidocr_onnxruntime import RapidOCR
cv2.setNumThreads(1)
CASES={
'JotMe测试': [('N01','V03',0,20,22,1,22.2),('N02','V03',1,46,48,2,48.84),('W01','V02',0,10,12,1,11.25),('W02a','V02',1,None,None,0,40.96),('W02b','V02',2,None,None,0,55.56),('W04','V01',0,12,14,1,13.85)],
'Palabra测试':[('N01','V01',0,46,48,1,46.34),('N02','V03',0,26,28,2,25.13),('C01','V04',0,28,30,2,29.53),('W01','V02',0,32,34,3,32.49),('W02','V02',1,68,70,4,66.28),('W03','V02',2,86,88,5,86.4),('W04','V02',3,118,120,5,117.79)],
'Maestra测试':[('N01','V01',0,14,16,1,26.4),('N02','V03',0,None,None,0,20.94),('W01','V02',0,8,10,1,21.63),('W02','V02',1,46,48,2,56.42),('W04','V02',2,78,80,2,88.69)],
'Wordly测试':[('N01','V01',0,16,18,1,None),('N02','V01',1,None,None,0,None),('N03','V01',2,None,None,0,67.57),('N04','V01',3,90,92,1,None),('B01','V02',0,12,14,1,27.22),('B02','V02',1,46,48,1,59.73),('W01a','V02',2,82,84,1,None),('W01b','V02',3,114,116,1,None),('W04','V02',4,None,None,0,None)],
'Parley测试':[('N01','V01',0,12,14,1,12.05),('N02','V01',1,36,38,2,37.52),('C01','V03',0,6,8,-1,8.1),('W01','V02',0,12,14,1,13.26),('W02','V02',1,50,52,2,51.28),('W03','V02',2,None,None,0,None),('W04','V02',3,84,86,4,85.14)]}
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def rect(prod,vid):
 if prod=='JotMe测试':return (0,200,700,800)
 if prod=='Palabra测试':return (430,130,950,1000)
 if prod=='Maestra测试':return (920,160,1910,890) if vid!='V02' else (450,120,1240,900)
 if prod=='Wordly测试':return (0,760,990,1000)
 return (310,230,1200,600)
def onset(y,sr,center,threshold=-42):
 a=max(0,round((center-.9)*sr));b=min(len(y),round((center+1.2)*sr));hop=160
 z=y[a:b];z=z[:len(z)//hop*hop].reshape(-1,hop);db=20*np.log10(np.sqrt((z*z).mean(1))+1e-12)
 active=np.flatnonzero(db>threshold)
 groups=np.split(active,np.where(np.diff(active)>10)[0]+1) if len(active) else []
 groups=[g for g in groups if len(g)>=5]
 if not groups:return None
 g=min(groups,key=lambda g:abs((a+g[0]*hop)/sr-center))
 return (a+int(g[0])*hop)/sr
def main():
 engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,rec_batch_num=1,use_cls=False,det_limit_type='max',det_limit_side_len=780)
 for prod,cases in CASES.items():
  out=ROOT/prod/'评测结果_20261103';manifest={x['id']:x for x in json.loads((out/'manifest.json').read_text(encoding='utf-8'))};results=[]
  for label,vid,idx,lo,hi,required,audio_start in cases:
   v=manifest[vid];events=json.loads((out/'raw'/f'{vid}_subtraction2.json').read_text(encoding='utf-8'))['events'];ev=events[idx]
   raw,sr=sf.read(out/v['tracks'][0]['file']);assist,rs=sf.read(out/'audio'/f'{vid}_target_assist2.wav');offset=v['tracks'][0]['sample0_video_pts_s']
   source_onsets={str(db):onset(raw,sr,ev['wav_s']+.05,db) for db in [-55,-50,-42]}
   result={'scene':label,'video':vid,'source_template_pts_s':ev['pts_s'],'source_onsets_wav_s':source_onsets,'source_pts_s':source_onsets['-50']+offset if source_onsets['-50'] is not None else None,'audio_asr_candidate_wav_s':audio_start}
   if audio_start is not None:
    sound={str(db):onset(assist,sr,audio_start,db) for db in [-50,-42,-35]}
    result['target_onsets_assist_wav_s']=sound
    result['target_audio_pts_s']=sound['-42']+offset if sound['-42'] is not None else None
    result['audio_delay_s']=result['target_audio_pts_s']-result['source_pts_s'] if result.get('target_audio_pts_s') is not None else None
   if lo is not None:
    cap=cv2.VideoCapture(str(ROOT/prod/v['path']));x1,y1,x2,y2=rect(prod,vid);cache={}
    def get(n):
     cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,im=cap.read();assert ok
     return im[y1:y2,x1:x2]
    def pred(n):
     if n not in cache:
      im=get(n);rr,_=engine(im);txt=' '.join(x[1] for x in (rr or []));cache[n]=txt
     txt=cache[n].lower()
     return bool(re.search('please|revised|send',txt)) if required==-1 else txt.count('please')>=required
    a=round(lo*30);b=round(hi*30)
    if pred(a) or not pred(b):
     result['subtitle_status']='bracket_failed';result['bracket_texts']=[cache[a],cache.get(b)]
    else:
     while b-a>1:
      mid=(a+b)//2
      if pred(mid):b=mid
      else:a=mid
     pts=json.loads((out/'raw'/f'{vid}_video_pts.json').read_text(encoding='utf-8'))['frames']
     paths=[]
     for n in [a,b]:
      f=out/'frames'/f'{label}_subtitle_{n:05d}.png';cv2.imencode('.png',get(n))[1].tofile(str(f));paths.append(str(f.relative_to(out)))
     result.update(subtitle_status='candidate_requires_visual_review',last_absent_frame=a,first_present_frame=b,subtitle_pts_s=float(pts[b]['best_effort_timestamp_time']),boundary_screenshots=paths)
     result['subtitle_delay_s']=result['subtitle_pts_s']-result['source_pts_s']
    result['ocr_trace']=[{'frame':n,'text':t} for n,t in sorted(cache.items())];cap.release()
   if prod=='Maestra测试' and label=='N02':
    result.update(source_pts_s=3.74,subtitle_pts_s=6.733,subtitle_delay_s=2.993,target_audio_pts_s=20.94,audio_delay_s=17.20,subtitle_status='reused_prior_visually_checked_adjacent_frames')
   results.append(result);save(out/'timing_candidates.json',results)
   print(prod,label, json.dumps({k:v for k,v in result.items() if k not in ['ocr_trace','bracket_texts']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
