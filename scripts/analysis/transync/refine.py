import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,os,json,argparse
from pathlib import Path
BASE=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102'))
sys.path.insert(0,str(BASE/'deps'))
import numpy as np,soundfile as sf
def save(name,data):(BASE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def crops():
    from faster_whisper import WhisperModel
    model=WhisperModel(str(BASE/'models'/'faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=5)
    specs=[('cold','normal',32,50),('clone_warm','normal',65,82.5),('default','normal',110,125.5),('delay','network',25,41),('interruption','network',52,68),('replay','network',68,85)]
    for label,key,start,end in specs:
        y,sr=sf.read(BASE/'audio'/f'{key}_mix.wav',dtype='float32');clip=y[round(start*sr):round(end*sr)]
        sf.write(BASE/'audio'/f'clip_{label}.wav',clip,sr,subtype='PCM_16')
        segs,info=model.transcribe(clip,language='en',beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=False,no_speech_threshold=None,log_prob_threshold=None)
        rows=[]
        for s in segs:
            row={'start_wav':s.start+start,'end_wav':s.end+start,'text':s.text,'words':[{'start_wav':w.start+start,'end_wav':w.end+start,'word':w.word,'p':w.probability} for w in s.words]}
            rows.append(row); print(label,round(row['start_wav'],3),round(row['end_wav'],3),s.text,flush=True)
        save(f'clip_{label}_asr.json',{'wav_offset':start,'video_pts_offset':-0.021,'segments':rows})
def onset():
    d={}
    for name in ['测试音频','声音克隆音频','normal_mix','network_mix']:
        y,sr=sf.read(BASE/'audio'/f'{name}.wav');hop=80
        z=y[:len(y)//hop*hop].reshape(-1,hop);db=20*np.log10(np.sqrt(np.mean(z*z,axis=1))+1e-12)
        intervals={}
        for th in [-60,-55,-50,-45,-40]:
            inds=np.flatnonzero(db>th)
            groups=np.split(inds,np.where(np.diff(inds)>40)[0]+1)
            intervals[str(th)]=[[round(float(g[0]*.005),3),round(float((g[-1]+1)*.005),3)] for g in groups if len(g)>4]
        d[name]=intervals
    save('onset_thresholds.json',d)
    print(json.dumps(d,ensure_ascii=False),flush=True)
def residual_asr():
    from faster_whisper import WhisperModel
    model=WhisperModel(str(BASE/'models'/'faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=4)
    d=json.loads((BASE/'source_subtraction.json').read_text(encoding='utf-8'))
    for label,key,test,a,b in [('warm_first','normal',59.57,6.7,11.0),('delay_first','network',16.52,7.5,12.5),('replay_fragment','network',68.50,9.6,11.1)]:
        row=next(x for x in d if x['key']==key and x['test']==test)
        y,sr=sf.read(BASE/'audio'/f'residual_{key}_{test:.2f}.wav',dtype='float32');clip=y[round(a*sr):round(b*sr)]
        segs,_=model.transcribe(clip,language='en',beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=False,no_speech_threshold=None,log_prob_threshold=None)
        data=[]
        for s in segs:
            v={'start_video_pts':s.start+row['offset_wav']+a-.021,'end_video_pts':s.end+row['offset_wav']+a-.021,'text':s.text,'words':[{'word':w.word,'start_video_pts':w.start+row['offset_wav']+a-.021,'end_video_pts':w.end+row['offset_wav']+a-.021,'p':w.probability} for w in s.words]}
            data.append(v);print(label,v['start_video_pts'],v['end_video_pts'],v['text'],flush=True)
        save(f'{label}_residual_asr.json',data)
if __name__=='__main__':{'crops':crops,'onset':onset,'residual_asr':residual_asr}[sys.argv[1]]()
