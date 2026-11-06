import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json,csv,shutil
from pathlib import Path
ROOT=(_PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs');SHARED=ROOT/'Transync测试/analysis_20261102';sys.path.insert(0,str(SHARED/'deps'))
import cv2,numpy as np,soundfile as sf
from PIL import Image,ImageDraw,ImageFont
cv2.setNumThreads(1)
PRODUCTS=['JotMe测试','Palabra测试','Maestra测试','Wordly测试','Parley测试']
FRAMES={'JotMe测试':{'V01':[37],'V02':[23,30,41,44,52,66],'V03':[39,70]},'Palabra测试':{'V01':[59],'V02':[46,70,100,132],'V03':[40],'V04':[43]},'Maestra测试':{'V01':[38],'V02':[33,55,68.5,100,190],'V03':[30]},'Wordly测试':{'V01':[28,64,82.8,100],'V02':[27,61,96,118,131,149]},'Parley测试':{'V01':[29,54],'V02':[32,54,76,104],'V03':[25]}}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
def images():
 for prod in PRODUCTS:
  out=ROOT/prod/'评测结果_20261103';manifest={v['id']:v for v in json.loads((out/'manifest.json').read_text(encoding='utf-8'))}
  for vid,times in FRAMES[prod].items():
   cap=cv2.VideoCapture(str(ROOT/prod/manifest[vid]['path']))
   for t in times:
    cap.set(cv2.CAP_PROP_POS_FRAMES,round(t*30));ok,im=cap.read();assert ok
    cv2.imencode('.png',im)[1].tofile(str(out/'frames'/f'{vid}_facts_{round(t*30):05d}.png'))
   cap.release()
  records=json.loads((out/'timing_candidates.json').read_text(encoding='utf-8'));panels=[]
  for row in records:
   paths=row.get('boundary_screenshots')
   if not paths:continue
   before=cv2.imdecode(np.fromfile(out/paths[0],dtype=np.uint8),1);after=cv2.imdecode(np.fromfile(out/paths[1],dtype=np.uint8),1)
   mask=cv2.cvtColor(cv2.absdiff(before,after),cv2.COLOR_BGR2GRAY)>24
   ys,xs=np.where(mask)
   if len(ys):
    x1=max(0,int(xs.min())-15);x2=min(after.shape[1],int(xs.max())+15);y1=max(0,int(ys.min())-12);y2=min(after.shape[0],int(ys.max())+12)
   else:x1,y1,x2,y2=0,0,after.shape[1],after.shape[0]
   pair=[]
   for im in [before,after]:
    crop=Image.fromarray(cv2.cvtColor(im[y1:y2,x1:x2],cv2.COLOR_BGR2RGB));scale=min(1,760/crop.width,180/crop.height);crop=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))))
    pair.append(crop)
   tile=Image.new('RGB',(800,440),'white');d=ImageDraw.Draw(tile);d.text((6,5),f'{prod} {row["scene"]} {row["subtitle_pts_s"]:.3f}s',font=font,fill='black');d.text((6,32),'before / after (changed area)',font=font,fill='black');tile.paste(pair[0],(10,60));tile.paste(pair[1],(10,245));panels.append(tile)
  for start in range(0,len(panels),8):
   batch=panels[start:start+8];canvas=Image.new('RGB',(1600,440*((len(batch)+1)//2)),'#dddddd')
   for i,im in enumerate(batch):canvas.paste(im,((i%2)*800,(i//2)*440))
   canvas.save(out/'frames'/f'字幕边界复核_{start//8+1}.jpg')
  print('IMAGES',prod,flush=True)
def plots():
 picks=[('JotMe测试','N01'),('Palabra测试','N01'),('Palabra测试','N02'),('Palabra测试','C01'),('Maestra测试','N01'),('Wordly测试','B01'),('Parley测试','N01'),('Parley测试','C01')]
 tiles=[]
 for prod,scene in picks:
  out=ROOT/prod/'评测结果_20261103';row=next(r for r in json.loads((out/'timing_candidates.json').read_text(encoding='utf-8')) if r['scene']==scene);vid=row['video'];center=row['audio_asr_candidate_wav_s'];a=max(0,center-1);b=center+2.5
  y,sr=sf.read(out/'audio'/f'{vid}_target_assist2.wav');seg=y[round(a*sr):round(b*sr)];hop=80;z=seg[:len(seg)//hop*hop].reshape(-1,hop);db=20*np.log10(np.sqrt((z*z).mean(1))+1e-12)
  tile=Image.new('RGB',(1000,320),'white');d=ImageDraw.Draw(tile);d.text((5,2),f'{prod} {scene} assist dBFS; WAV time',font=font,fill='black')
  def xx(t):return 60+(t-a)/(b-a)*920
  def yy(v):return 280-(max(-80,min(0,v))+80)/80*230
  for val in [-70,-60,-50,-42,-35,-20,0]:d.line((60,yy(val),980,yy(val)),fill='#cccccc');d.text((5,yy(val)-10),str(val),font=font,fill='black')
  for t in np.arange(np.ceil(a*2)/2,b,.5):d.line((xx(t),45,xx(t),282),fill='#eeeeee');d.text((xx(t)-20,285),f'{t:.1f}',font=font,fill='black')
  pts=[(xx(a+i*.005),yy(float(v))) for i,v in enumerate(db)];d.line(pts,fill='#195e9c',width=2)
  for val,color in [(center,'#aa2222'),(row.get('target_audio_pts_s',center)+.021 if row.get('target_audio_pts_s') else center,'#22aa22')]:d.line((xx(val),40,xx(val),282),fill=color,width=2)
  tiles.append(tile)
 canvas=Image.new('RGB',(2000,1280),'white')
 for i,t in enumerate(tiles):canvas.paste(t,((i%2)*1000,(i//2)*320))
 canvas.save(ROOT/'JotMe测试/评测结果_20261103/_support/首响候选波形.png')
def direct_asr():
 from faster_whisper import WhisperModel
 model=WhisperModel(str(SHARED/'models/faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=5,num_workers=1)
 for prod in PRODUCTS:
  out=ROOT/prod/'评测结果_20261103';rows=[]
  for clip in json.loads((out/'sound_quality.json').read_text(encoding='utf-8')):
   y,sr=sf.read(out/clip['path'],dtype='float32');segs,info=model.transcribe(y,language='en',beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
   ss=[]
   for s in segs:ss.append({'start':s.start,'end':s.end,'text':s.text,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in s.words]})
   rows.append({'id':clip['id'],'source':clip['path'],'segments':ss});print(prod,clip['id'],' '.join(s['text'] for s in ss),flush=True)
  (out/'direct_clean_asr.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
def palabra_normal():
 from faster_whisper import WhisperModel
 out=ROOT/'Palabra测试/评测结果_20261103';y,sr=sf.read(out/'audio/V03_track1.wav',dtype='float32');clip=y[round(27.3*sr):round(39.2*sr)]
 sf.write(out/'audio/N02_full_clean.wav',clip,sr,subtype='PCM_16')
 model=WhisperModel(str(SHARED/'models/faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=5,num_workers=1)
 segs,info=model.transcribe(clip,language='en',beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
 rows=[{'start':s.start,'end':s.end,'text':s.text} for s in segs];result={'source':'audio/N02_full_clean.wav','original_wav_s':[27.3,39.2],'source_ends_before_clip':True,'segments':rows}
 (out/'N02_full_clean_asr.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':{'images':images,'plots':plots,'direct_asr':direct_asr,'palabra_normal':palabra_normal}[sys.argv[1]]()
