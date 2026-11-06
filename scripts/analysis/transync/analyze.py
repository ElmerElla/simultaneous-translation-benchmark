import os as _publication_os
from pathlib import Path as _PublicationPath
import os,sys,json,time,argparse
from pathlib import Path
BASE=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102'))
sys.path.insert(0,str(BASE/'deps'))
os.environ.update(HF_HOME=str(BASE/'models'/'hf'),HF_HUB_DISABLE_XET='1',HF_HUB_DISABLE_SYMLINKS_WARNING='1')
import numpy as np
import soundfile as sf
def save(name,data):
    (BASE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def ocr():
    import cv2
    from rapidocr_onnxruntime import RapidOCR
    engine=RapidOCR(intra_op_num_threads=3,inter_op_num_threads=1)
    for key,filename in [('normal','冷启动、正常翻译、关闭音色克隆翻译.mkv'),('network','延迟100ms、中断10s测试.mkv')]:
        cap=cv2.VideoCapture(str(BASE.parent/'outputs'/filename))
        records=[]
        duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/30
        for sec in np.arange(0,duration,1):
            cap.set(cv2.CAP_PROP_POS_FRAMES,round(sec*30));ok,img=cap.read()
            if not ok:continue
            result,_=engine(img[:850,:960])
            rows=[] if result is None else [{'box':np.array(box).tolist(),'text':text,'confidence':float(score)} for box,text,score in result]
            if key=='network' and sec%2==0:
                right,_=engine(img[200:900,960:])
                if right:
                    rows.extend([{'box':(np.array(box)+[960,200]).tolist(),'text':text,'confidence':float(score)} for box,text,score in right])
            records.append({'frame':round(sec*30),'pts':round(sec,3),'items':rows})
            save(f'{key}_ocr_coarse.json',records)
            if int(sec)%10==0: print('OCR',key,sec,flush=True)
        cap.release()
        save(f'{key}_ocr_coarse.json',records)
def asr():
    from faster_whisper import WhisperModel
    model=WhisperModel(str(BASE/'models'/'faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=6,num_workers=1)
    for p in [BASE/'audio'/'测试音频.wav',BASE/'audio'/'声音克隆音频.wav']+[BASE/'audio'/f'{key}_{track}.wav' for key in ['normal','network'] for track in ['source','translated']]:
        lang='en' if 'translated' in p.stem else 'zh'
        samples,sr=sf.read(p,dtype='float32'); assert sr==16000
        segs,info=model.transcribe(samples,language=lang,beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
        result=[]
        for seg in segs:
            row={'start':seg.start,'end':seg.end,'text':seg.text,'avg_logprob':seg.avg_logprob,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in seg.words]}
            result.append(row)
            print(p.stem,round(seg.start,3),round(seg.end,3),seg.text,flush=True)
        save(f'{p.stem}_asr.json',{'model':'Systran/faster-whisper-small','language':lang,'audio_sample0_video_pts':-0.021 if p.stem.startswith(('normal','network')) else 0,'segments':result})
def stats():
    from scipy.signal import correlate,find_peaks
    result={}
    for p in (BASE/'audio').glob('*.wav'):
        y,sr=sf.read(p);hop=160
        z=y[:len(y)//hop*hop].reshape(-1,hop)
        rms=np.sqrt(np.mean(z*z,axis=1));db=20*np.log10(rms+1e-12)
        intervals=[];active=db>-42
        # Join gaps under 300ms, retain voiced chunks at least 80ms.
        indices=np.flatnonzero(active)
        if len(indices):
            groups=np.split(indices,np.where(np.diff(indices)>30)[0]+1)
            intervals=[[round(g[0]*.01,3),round((g[-1]+1)*.01,3)] for g in groups if len(g)>=8]
        result[p.stem]={'duration':len(y)/sr,'peak':float(np.max(np.abs(y))),'rms_db':float(20*np.log10(np.sqrt(np.mean(y*y))+1e-12)),'voiced_intervals_wav_seconds':intervals}
        np.savez_compressed(BASE/'audio'/f'{p.stem}_rms.npz',db=db)
    ref,sr=sf.read(BASE/'audio'/'测试音频.wav');ref=ref[::4]
    for key in ['normal','network']:
        y,sr=sf.read(BASE/'audio'/f'{key}_source.wav');y=y[::4]
        c=correlate(y,ref,mode='valid',method='fft')
        cumulative=np.concatenate(([0.0],np.cumsum(y*y)))
        norm=np.sqrt(np.maximum(1e-16,(cumulative[len(ref):]-cumulative[:-len(ref)])*np.sum(ref*ref)))
        corr=c/norm
        peaks,_=find_peaks(corr,height=.2,distance=4000*10)
        result[key+'_source_alignment']=[{'wav_offset_seconds':float(i/4000),'video_offset_seconds':float(i/4000-.021),'correlation':float(corr[i])} for i in peaks]
    save('audio_stats.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':
    {'ocr':ocr,'asr':asr,'stats':stats}[sys.argv[1]]()
