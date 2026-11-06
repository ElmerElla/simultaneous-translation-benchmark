import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,os,json,hashlib,subprocess
from pathlib import Path
BASE=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102')); ROOT=BASE.parent; OUT=BASE/'loss10';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(BASE/'deps'))
os.environ.update(HF_HOME=str(BASE/'models'/'hf'),HF_HUB_DISABLE_XET='1')
SRC=ROOT/'outputs'/'补录10%丢包.mkv'
def save(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def run(args):return subprocess.run(args,check=True,capture_output=True).stdout
def prepare():
 from PIL import Image,ImageDraw
 probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(SRC)]));save('probe.json',probe)
 for stream in ['v:0','a:0']:
  save(stream.replace(':','_')+'_frame_pts.json',json.loads(run(['ffprobe','-v','error','-select_streams',stream,'-show_frames','-show_entries','frame=pts_time,best_effort_timestamp_time,nb_samples','-of','json',str(SRC)])))
 save('packet_pts.json',json.loads(run(['ffprobe','-v','error','-show_packets','-show_entries','packet=stream_index,pts_time,dts_time,duration_time,flags','-of','json',str(SRC)])))
 hashes={}
 for i,key in [(1,'mix'),(2,'source'),(3,'translated')]:
  p=OUT/f'{key}.wav';run(['ffmpeg','-v','error','-y','-i',str(SRC),'-map',f'0:{i}','-ac','1','-ar','16000','-c:a','pcm_s16le',str(p)]);hashes[key]=hashlib.sha256(p.read_bytes()).hexdigest()
 run(['ffmpeg','-v','error','-y','-i',str(SRC),'-vf',"select=not(mod(n\\,90)),scale=640:-1",'-fps_mode','vfr',str(OUT/'overview_%03d.jpg')])
 imgs=sorted(OUT.glob('overview_*.jpg'));canvas=Image.new('RGB',(1280,390*((len(imgs)+1)//2)),'#dddddd');draw=ImageDraw.Draw(canvas)
 for i,p in enumerate(imgs):
  x=i%2*640;y=i//2*390;canvas.paste(Image.open(p),(x,y+25));draw.text((x+10,y+5),f'packet loss: t={i*3:.3f}s',fill='black')
 canvas.save(OUT/'contact.jpg');save('manifest.json',{'path':str(SRC.relative_to(ROOT)),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'duration':probe['format']['duration'],'audio_hashes':hashes,'tracks_identical':len(set(hashes.values()))==1})
 print(json.dumps({'duration':probe['format']['duration'],'tracks_identical':len(set(hashes.values()))==1}),flush=True)
def ocr():
 import cv2,numpy as np
 from rapidocr_onnxruntime import RapidOCR
 engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)
 cap=cv2.VideoCapture(str(SRC));records=[]
 for sec in range(35):
  cap.set(cv2.CAP_PROP_POS_FRAMES,sec*30);ok,img=cap.read()
  if not ok:break
  rows=[]
  for crop,offset in [(img[:900,:960],[0,0]),(img[550:1000,960:],[960,550])]:
   result,_=engine(crop)
   if result:rows += [{'text':t,'confidence':float(s),'box':(np.array(b)+offset).tolist()} for b,t,s in result]
  records.append({'frame':sec*30,'pts':sec,'items':rows});save('ocr_coarse.json',records)
  print('OCR',sec,' || '.join(x['text'] for x in rows),flush=True)
 cap.release()
def asr():
 import numpy as np,soundfile as sf
 from scipy.signal import correlate,find_peaks
 from faster_whisper import WhisperModel
 y,sr=sf.read(OUT/'mix.wav',dtype='float32');ref,rsr=sf.read(BASE/'audio'/'测试音频.wav',dtype='float32')
 model=WhisperModel(str(BASE/'models'/'faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=5)
 for lang in ['zh','en']:
  segs,_=model.transcribe(y,language=lang,beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
  rows=[]
  for s in segs:
   row={'start_wav':s.start,'end_wav':s.end,'text':s.text,'words':[{'word':w.word,'start_wav':w.start,'end_wav':w.end,'p':w.probability} for w in s.words]};rows.append(row);print(lang,round(s.start,3),round(s.end,3),s.text,flush=True)
  save(f'asr_{lang}.json',rows)
 z=y[::4].astype(float);r=ref[::4].astype(float);c=correlate(z,r,mode='valid',method='fft');cum=np.concatenate(([0.0],np.cumsum(z*z)));norm=np.sqrt(np.maximum(1e-16,(cum[len(r):]-cum[:-len(r)])*np.sum(r*r)));corr=c/norm;peaks,_=find_peaks(corr,height=.2,distance=4000*10)
 intervals={};hop=80;win=y[:len(y)//hop*hop].reshape(-1,hop);db=20*np.log10(np.sqrt(np.mean(win*win,axis=1))+1e-12)
 for th in [-60,-55,-50,-45,-40]:
  ix=np.flatnonzero(db>th);groups=np.split(ix,np.where(np.diff(ix)>40)[0]+1);intervals[str(th)]=[[float(g[0]*.005),float((g[-1]+1)*.005)] for g in groups if len(g)>4]
 result={'source_alignments':[{'wav_offset':float(p/4000),'video_offset':float(p/4000-.021),'correlation':float(corr[p])} for p in peaks],'threshold_intervals_wav':intervals,'wav_duration':len(y)/sr,'sample0_video_pts':-.021,'peak':float(np.max(np.abs(y))),'clipped_ratio':float(np.mean(np.abs(y)>=.999))};save('audio_analysis.json',result);print(json.dumps(result),flush=True)
def refine():
 import numpy as np,soundfile as sf,cv2
 from scipy.signal import correlate
 from scipy.ndimage import shift
 from faster_whisper import WhisperModel
 from rapidocr_onnxruntime import RapidOCR
 y,sr=sf.read(OUT/'mix.wav',dtype='float32');prior,_=sf.read(BASE/'audio'/'normal_mix.wav',dtype='float32');ref=prior[round(15.1*sr):round(28.1*sr)]
 a=round(8.2*sr);c=correlate(y[a:round(12.4*sr)],ref[:4*sr],mode='valid',method='fft');peak=int(np.argmax(c));delta=float(.5*(c[peak-1]-c[peak+1])/(c[peak-1]-2*c[peak]+c[peak+1]));offset=a+peak;template=shift(ref,delta,order=3,mode='nearest');target=y[offset:offset+len(ref)];gain=float(np.dot(target[:4*sr],template[:4*sr])/np.dot(template[:4*sr],template[:4*sr]));residual=target-gain*template;sf.write(OUT/'source_residual.wav',residual,sr,subtype='PCM_16')
 meta={'template':'normal_mix.wav 15.1～28.1秒','offset_wav':offset/sr,'fractional_sample_shift':delta,'gain':gain,'correlation_first4sec':float(np.corrcoef(target[:4*sr],template[:4*sr])[0,1]),'noise_rms_first4sec':float(np.sqrt(np.mean(residual[:4*sr]**2)))}
 hop=80;z=residual[:len(residual)//hop*hop].reshape(-1,hop);db=20*np.log10(np.sqrt(np.mean(z*z,axis=1))+1e-12);intervals={}
 for th in [-55,-50,-45,-40,-35]:
  ix=np.flatnonzero(db>th);groups=np.split(ix,np.where(np.diff(ix)>40)[0]+1);intervals[str(th)]=[[float(offset/sr+g[0]*.005-.021),float(offset/sr+(g[-1]+1)*.005-.021)] for g in groups if len(g)>4]
 meta['residual_intervals_video_pts']=intervals;save('source_subtraction.json',meta);print(json.dumps(meta),flush=True)
 model=WhisperModel(str(BASE/'models'/'faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=4)
 for name,clip,wav_start in [('output_crop',y[round(14*sr):round(31*sr)],14),('first_sentence_residual',residual[round(6.5*sr):],offset/sr+6.5)]:
  segs,_=model.transcribe(clip,language='en',beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=False,no_speech_threshold=None,log_prob_threshold=None);rows=[]
  for s in segs:
   row={'start_video_pts':s.start+wav_start-.021,'end_video_pts':s.end+wav_start-.021,'text':s.text,'words':[{'word':w.word,'start_video_pts':w.start+wav_start-.021,'end_video_pts':w.end+wav_start-.021,'p':w.probability} for w in s.words]};rows.append(row);print(name,row['start_video_pts'],row['end_video_pts'],s.text,flush=True)
  save(name+'_asr.json',rows)
 engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1);cap=cv2.VideoCapture(str(SRC));trace=[]
 def get(n):cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,f=cap.read();assert ok;return f
 def pred(n):
  img=get(n);r,_=engine(img[275:530,:950]);text=' '.join(x[1] for x in r) if r else '';ok='please' in text.lower() or 'confirm' in text.lower();trace.append({'frame':n,'pts':n/30,'text':text,'match':ok});return ok
 a=13*30;b=15*30;assert not pred(a) and pred(b)
 while b-a>1:
  mid=(a+b)//2
  if pred(mid):b=mid
  else:a=mid
 for n in [a,b]:cv2.imencode('.png',get(n))[1].tofile(str(OUT/f'subtitle_boundary_{n}.png'))
 save('subtitle_event.json',{'last_absent_frame':a,'first_present_frame':b,'last_absent_pts':a/30,'first_present_pts':b/30,'traces':trace});print('SUBTITLE',b,b/30,flush=True)
 # Refine only configuration-state transitions; this is not measured packet loss.
 cfg=[]
 def active(n):
  img=get(n);r,_=engine(img[685:750,960:]);text=' '.join(x[1] for x in r) if r else '';cfg.append({'frame':n,'pts':n/30,'text':text});return '10%' in text or '10％' in text
 trans=[]
 for label,lo,hi,want in [('applied',2,3,True),('removed',32,34,False)]:
  a=lo*30;b=hi*30;assert active(a)!=want and active(b)==want,(label,cfg[-2:])
  while b-a>1:
   mid=(a+b)//2
   if active(mid)==want:b=mid
   else:a=mid
  for n in [a,b]:cv2.imencode('.png',get(n))[1].tofile(str(OUT/f'{label}_{n}.png'))
  trans.append({'event':label,'before_frame':a,'after_frame':b,'before_pts':a/30,'after_pts':b/30})
 save('configuration_events.json',{'events':trans,'traces':cfg});print('CONFIG',json.dumps(trans),flush=True)
 cap.release()
def final():
 import numpy as np,soundfile as sf
 from faster_whisper import WhisperModel
 y,sr=sf.read(OUT/'mix.wav',dtype='float32');res,_=sf.read(OUT/'source_residual.wav',dtype='float32');sub=json.loads((OUT/'source_subtraction.json').read_text(encoding='utf-8'));cut=round((sub['offset_wav']+len(res)/sr)*sr);start=round(7.5*sr);clip=np.concatenate((res[start:],y[cut:31*sr]));clip_start=sub['offset_wav']+7.5
 sf.write(OUT/'output_asr_assist.wav',clip,sr,subtype='PCM_16')
 model=WhisperModel(str(BASE/'models'/'faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=4)
 segs,_=model.transcribe(clip,language='en',beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=False,no_speech_threshold=None,log_prob_threshold=None);rows=[]
 for s in segs:
  row={'start_video_pts':s.start+clip_start-.021,'end_video_pts':s.end+clip_start-.021,'text':s.text,'words':[{'word':w.word,'start_video_pts':w.start+clip_start-.021,'end_video_pts':w.end+clip_start-.021,'p':w.probability} for w in s.words]};rows.append(row);print('ASSIST',row['start_video_pts'],row['end_video_pts'],s.text,flush=True)
 save('output_assist_asr.json',rows)
 audio=json.loads((OUT/'audio_analysis.json').read_text(encoding='utf-8'));event=json.loads((OUT/'subtitle_event.json').read_text(encoding='utf-8'));cfg=json.loads((OUT/'configuration_events.json').read_text(encoding='utf-8'));source_wav=8.310;source_pts=source_wav-.021;subtitle_pts=event['first_present_pts'];audio_pts=16.387375;audio_end=29.675-.021;word=json.loads((OUT/'asr_zh.json').read_text(encoding='utf-8'))[0]['words'][0];word_pts=word['start_wav']-.021
 tail=y[round(21.3*sr):30*sr];tailpeak=float(np.max(np.abs(tail)));tailclip=float(np.mean(np.abs(tail)>=.999))
 data={'id':'W04','scene':'上下行各10%概率丢包·克隆开启','source_wav':source_wav,'source_pts':source_pts,'source_first_word_pts':word_pts,'subtitle_pts':subtitle_pts,'audio_pts':audio_pts,'audio_end_pts':audio_end,'subtitle_latency':subtitle_pts-source_pts,'audio_latency':audio_pts-source_pts,'subtitle_latency_word':subtitle_pts-word_pts,'audio_latency_word':audio_pts-word_pts,'subtitle_to_audio_gap':audio_pts-subtitle_pts,'audio_span':audio_end-audio_pts,'source_to_audio_end':audio_end-source_pts,'configuration':{'uplink_probability':.1,'downlink_probability':.1,'configured_duration':30,'active_first_pts':cfg['events'][0]['after_pts'],'inactive_first_pts':cfg['events'][1]['after_pts'],'ui_active_span':cfg['events'][1]['after_pts']-cfg['events'][0]['after_pts'],'real_packet_loss_measured':False,'coverage_verified':False,'cloning_enabled':True},'quality':{'pure_tail_wav_start':21.3,'pure_tail_wav_end':30,'peak':tailpeak,'clipped_sample_ratio':tailclip,'observed_phrase_gaps':[24.730-23.775,27.075-26.545],'subjective_listening':False},'facts':[{'id':'F1','source':'下周二上午十点前确认测试结果','keyword':'Please confirm the test results by 10:00 a.m. next Tuesday.','subtitle':'正确','audio':'正确（抵消辅助）'},{'id':'F2','source':'预算上限三万元','keyword':'The budget cap is 30,000 yuan','subtitle':'正确','audio':'正确（抵消辅助）'},{'id':'F3','source':'不是十三万元','keyword':'not 130,000 yuan','subtitle':'正确','audio':'正确'},{'id':'F4','source':'只有测试通过才发布','keyword':'Only release after passing the tests','subtitle':'正确','audio':'正确'},{'id':'F5','source':'发现问题则推迟到周五','keyword':'If any issues are discovered, postpone them until Friday.','subtitle':'正确','audio':'正确'}],'manifest':json.loads((OUT/'manifest.json').read_text(encoding='utf-8')),'limitations':['工具只显示配置上/下行10%，实测丢弃比例未采集，业务覆盖待验证。','1条样本，无统计稳定性结论。进程已在录像开始时打开，此条不记冷启动。','三音轨解码后相同，首句/预算与源音重叠，用同源抵消辅助ASR；不据此作完整音质或新声纹主比较。','会话结束附近工具显示控制对象变无，未单独验证撤销后恢复表现。']}
 assert len(event['traces'])>0 and event['first_present_frame']==event['last_absent_frame']+1
 pts=json.loads((OUT/'v_0_frame_pts.json').read_text(encoding='utf-8'))['frames'];assert abs(float(pts[event['first_present_frame']]['pts_time'])-subtitle_pts)<.0006
 assert data['configuration']['active_first_pts']<source_pts<subtitle_pts<audio_pts<audio_end<data['configuration']['inactive_first_pts']
 save('results.json',data);print(json.dumps(data,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'ocr':ocr,'asr':asr,'refine':refine,'final':final}[sys.argv[1]]()
