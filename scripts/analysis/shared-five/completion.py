import os as _publication_os
from pathlib import Path as _PublicationPath
"""Offline startup stages and bounded subtitle/voice completion evidence."""
import sys,json,csv
from pathlib import Path
ROOT=(_PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs');SHARED=ROOT/'Transync测试/analysis_20261102'
sys.path.insert(0,str(SHARED/'deps'))
import cv2,numpy as np,soundfile as sf
from PIL import Image,ImageDraw,ImageFont
from rapidocr_onnxruntime import RapidOCR
from measure import rect
cv2.setNumThreads(1)
BRACKETS={
'JotMe测试':[('N01','V03',34,36,1),('N02','V03',60,62,3),('W01','V02',20,22,1),('W04','V01',34,36,1)],
'Maestra测试':[('N01','V01',24,26,1),('N02','V03',18,20,1),('W01','V02',20,22,1),('W02','V02',54,56,2),('W04','V02',86,88,2)],
'Wordly测试':[('N01','V01',26,28,1),('N04','V01',98,100,1),('B01','V02',24,26,1),('B02','V02',58,60,1),('W01a','V02',94,96,1),('W01b','V02',116,118,1)],
'Parley测试':[('N01','V01',20,22,1),('N02','V01',46,48,2),('C01','V03',16,18,1),('W01','V02',22,24,1),('W02','V02',52,54,2),('W03','V02',68,70,3),('W04','V02',92,100,4)]}
# Search only terminal-phrase windows confirmed by transcript and the isolated original waveform.
ENDS={
'JotMe测试':{'N01':(36.5,38),'N02':(67.8,69.2),'W01':(22.5,24),'W04':(36.5,37.9)},
'Palabra测试':{'N01':(57.7,59),'N02':(38.4,39.6),'C01':(41.7,43),'W01':(44.7,46),'W02':(68,69.2),'W03':(98.6,99.9),'W04':(130.1,131.5)},
'Maestra测试':{'N01':(38,39.3),'N02':(32.8,34),'W01':(32.9,34.2),'W02':(67.8,69),'W04':(100.2,101.5)},
'Wordly测试':{'N03':(82,83.2),'B01':(41.7,43),'B02':(74.3,75.5)},
'Parley测试':{'N01':(28.3,29.6),'N02':(53.3,54.5),'C01':(23.1,24.4),'W01':(31,32.2),'W04':(101.4,102.7)}}
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,rec_batch_num=1,use_cls=False,det_limit_type='max',det_limit_side_len=960)
 for prod in ['JotMe测试','Palabra测试','Maestra测试','Wordly测试','Parley测试']:
  out=ROOT/prod/'评测结果_20261103';d=json.loads((out/'reviewed_results.json').read_text(encoding='utf-8'));vs={v['id']:v for v in json.loads((out/'manifest.json').read_text(encoding='utf-8'))};found={}
  for scene,vid,lo,hi,count in BRACKETS.get(prod,[]):
   cap=cv2.VideoCapture(str(out.parent/vs[vid]['path']));crop=rect(prod,vid)
   if prod=='Parley测试' and scene=='W04':crop=(310,230,1200,800)
   cache={}
   def get(n):
    cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,im=cap.read();assert ok
    x1,y1,x2,y2=crop;return im[y1:y2,x1:x2]
   def pred(n):
    if n not in cache:
     rr,_=engine(get(n));cache[n]=' '.join(x[1] for x in (rr or []))
    return cache[n].lower().count('friday')>=count
   a,b=round(lo*30),round(hi*30)
   if pred(a) or not pred(b):
    found[scene]={'status':'bracket_failed','bracket':[a,b],'texts':cache};print(prod,scene,'BRACKET FAILED',cache,flush=True)
   else:
    while b-a>1:
     mid=(a+b)//2
     if pred(mid):b=mid
     else:a=mid
    paths=[]
    for n in [a,b]:
     f=out/'frames'/f'{scene}_tail_{n:05d}.png';cv2.imencode('.png',get(n))[1].tofile(str(f));paths.append(str(f.relative_to(out)))
    found[scene]={'status':'adjacent_frame_candidate','subtitle_tail_pts_s':b/30,'last_absent_frame':a,'first_present_frame':b,'screenshots':paths,'ocr_trace':cache};print(prod,scene,'TAIL',b/30,flush=True)
   cap.release()
  if prod=='Palabra测试':
   for t in d['timing']:found[t['scene']]={'status':'whole_history_block_appears_at_once','subtitle_tail_pts_s':t.get('subtitle_pts_s'),'screenshots':t.get('boundary_screenshots',[]),'note':'新历史块整段出现；复核首显相邻帧中的末句，不按旧块Friday计时。'}
  for t in d['timing']:
   r=found.setdefault(t['scene'],{'status':'unconfirmed','note':'无法分离本轮新字幕/残段的完成，保留未确认。'});r['scene']=t['scene'];r['video']=t['video'];r['source_pts_s']=t['source_pts_s']
   if t['scene'] in ENDS[prod]:
    a,b=ENDS[prod][t['scene']];y,sr=sf.read(out/'audio'/f'{t["video"]}_track1.wav');hop=160
    z=y[round(a*sr):round(b*sr)];z=z[:len(z)//hop*hop].reshape(-1,hop);db=20*np.log10(np.sqrt((z*z).mean(1))+1e-12)
    thresholds={}
    for threshold in [-50,-42,-35]:
     active=np.flatnonzero(db>threshold);groups=np.split(active,np.where(np.diff(active)>5)[0]+1) if len(active) else [];groups=[g for g in groups if len(g)>=4]
     thresholds[str(threshold)]=a+(groups[-1][-1]+1)*.01-.021 if groups else None
    r.update(audio_tail_search_wav_s=[a,b],audio_tail_threshold_candidates=thresholds,audio_end_pts_s=thresholds['-50'],audio_end_method='原混音无重叠尾词，10ms RMS −50dBFS；−42/−35候选保留；约0.1秒尺度，非绝对同步标定。')
   else:r.update(audio_end_pts_s=None,audio_end_method='未录得独立本轮译音，或中断/同文重播重叠，无法分离完成时刻。')
   if prod=='JotMe测试' and t['scene']=='N02':r['note']='字幕先完成尾句，随后重复发布/延期条件；声音完成包括重复尾句。'
   if prod=='JotMe测试' and t['scene']=='N01':r['note']='此处为首段尾句首次完整；随后画面另出现孤立Friday，不能据首次完整帧断言后续不再变化。'
   if prod=='Wordly测试' and t['scene']=='W01b':r['note']='记录首次新尾句，随后约123秒仍有重复同文，排队结束与单轮完成归属不明。'
   if prod=='Parley测试' and t['scene'] in ['W02','W03']:r['note']='中断残段/恢复重播合并文本的尾部事件；不代表准确补译或可归属单轮完整输出。'
   if prod=='Wordly测试' and t['scene']=='N03':r['note']='对应新字幕无法区分；独立有声段末尾跨越约76秒配置切换，不是纯正常条件全段。'
  write(out/'completion_candidates.json',list(found.values()))
  # Contact sheets retain before/after terminal-word boundaries for visual review.
  tiles=[];font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
  for r in found.values():
   if not r.get('screenshots'):continue
   tile=Image.new('RGB',(850,370),'white');draw=ImageDraw.Draw(tile);draw.text((5,3),f'{prod} {r["scene"]} tail {r.get("subtitle_tail_pts_s")}',font=font,fill='black')
   for i,p in enumerate(r['screenshots']):
    im=Image.open(out/p);im.thumbnail((830,150));tile.paste(im,(8,32+165*i))
   tiles.append(tile)
  for start in range(0,len(tiles),8):
   ts=tiles[start:start+8];canvas=Image.new('RGB',(1700,370*((len(ts)+1)//2)),'#ddd')
   for i,im in enumerate(ts):canvas.paste(im,((i%2)*850,(i//2)*370))
   canvas.save(out/'frames'/f'尾句完成边界复核_{start//8+1}.jpg')
  print(prod,'AUDIO ENDS',[(r['scene'],r.get('audio_end_pts_s'),r.get('audio_tail_threshold_candidates')) for r in found.values()],flush=True)
if __name__=='__main__':main()
