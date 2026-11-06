import os as _publication_os
from pathlib import Path as _PublicationPath
"""Offline video analysis. Reuses existing local models, never calls product services.
Run with bundled Python: analyze.py prepare|ocr|asr [product].
All text outputs are UTF-8. Raw media are read-only.
"""
import sys, os, json, hashlib, subprocess, time
from pathlib import Path
ROOT = _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))
SHARED = ROOT/'outputs/Transync测试/analysis_20261102'
sys.path.insert(0, str(SHARED/'deps'))
import numpy as np
import soundfile as sf
PRODUCTS = ['JotMe测试','Palabra测试','Maestra测试','Wordly测试','Parley测试']
OUTNAME = '评测结果_20261103'

def save(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
def run(args):
    return subprocess.check_output(args, stderr=subprocess.PIPE)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def products():
    return PRODUCTS if len(sys.argv)<3 else [sys.argv[2]]
def prep():
    from scipy.signal import correlate, find_peaks
    for name in products():
        base=ROOT/'outputs'/name; out=base/OUTNAME
        for d in ['audio','frames','raw','_support']: (out/d).mkdir(parents=True,exist_ok=True)
        videos=sorted(list(base.glob('*.mkv'))+list((base/'outputs').glob('*.mkv')))
        manifest=[]
        for n, video in enumerate(videos):
            key=f'V{n+1:02}'
            probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]))
            save(out/'raw'/f'{key}_probe.json',probe)
            pts=json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=pts_time,best_effort_timestamp_time','-of','json',str(video)]))
            save(out/'raw'/f'{key}_video_pts.json',pts)
            tracks=[]
            for s in probe['streams']:
                if s['codec_type']!='audio': continue
                dest=out/'audio'/f'{key}_track{s["index"]}.wav'
                if not dest.exists():run(['ffmpeg','-v','error','-y','-i',str(video),'-map',f'0:{s["index"]}','-ac','1','-ar','16000','-c:a','pcm_s16le',str(dest)])
                y,sr=sf.read(dest,dtype='int16')
                tracks.append({'stream':s['index'],'file':str(dest.relative_to(out)),'pcm_sha256':hashlib.sha256(y.tobytes()).hexdigest(),'samples':len(y),'sample_rate':sr,'sample0_video_pts_s':float(s.get('start_time',0))})
            manifest.append({'id':key,'path':str(video.relative_to(base)),'sha256':sha(video),'duration_s':float(probe['format']['duration']),'tracks':tracks,'tracks_identical':len({x['pcm_sha256'] for x in tracks})==1})
            y,sr=sf.read(out/tracks[0]['file']);hop=160
            z=y[:len(y)//hop*hop].reshape(-1,hop); db=20*np.log10(np.sqrt((z*z).mean(1))+1e-12)
            active=np.flatnonzero(db>-42);groups=np.split(active,np.where(np.diff(active)>25)[0]+1) if len(active) else []
            intervals=[[float(g[0]*.01),float((g[-1]+1)*.01)] for g in groups if len(g)>=6]
            save(out/'raw'/f'{key}_energy.json',{'hop_s':.01,'threshold_db':-42,'intervals_wav_s':intervals,'peak':float(np.abs(y).max()),'clipping_fraction':float((np.abs(y)>=.999).mean())})
            np.savez_compressed(out/'audio'/f'{key}_rms.npz',db=db)
            # Compare two local candidate references; low correlations are not used as truth.
            refs={'transync_input':SHARED/'audio/测试音频.wav','maestra_source':ROOT/'outputs/Maestra测试/analysis_20261102/audio/mix.wav'}
            matches={}
            for refname,path in refs.items():
                r,rs=sf.read(path)
                if refname=='maestra_source':r=r[round(3.7*rs):round(16.65*rs)]
                a=y[::4];r=r[::4]
                if len(a)<len(r):continue
                c=correlate(a,r,mode='valid',method='fft');cs=np.r_[0.,np.cumsum(a*a)]
                c=c/np.sqrt(np.maximum(1e-18,(cs[len(r):]-cs[:-len(r)])*np.sum(r*r)))
                peaks,_=find_peaks(c,height=.15,distance=16000/4*8)
                matches[refname]=[{'wav_s':float(i/4000),'pts_s':float(i/4000+tracks[0]['sample0_video_pts_s']),'correlation':float(c[i])} for i in peaks]
            save(out/'raw'/f'{key}_reference_matches.json',matches)
            print(name,key,video.name,manifest[-1]['duration_s'],'identical',manifest[-1]['tracks_identical'],matches,flush=True)
        save(out/'manifest.json',manifest)
        source=Path(__file__).read_text(encoding='utf-8')
        (out/'_support/analyze.py').write_text(source,encoding='utf-8')

def ocr():
    import cv2
    from rapidocr_onnxruntime import RapidOCR
    cv2.setNumThreads(1)
    engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,rec_batch_num=1,use_cls=False,det_limit_type='max',det_limit_side_len=780)
    for name in products():
        base=ROOT/'outputs'/name;out=base/OUTNAME
        for v in json.loads((out/'manifest.json').read_text(encoding='utf-8')):
            dest=out/'raw'/f'{v["id"]}_ocr.json'
            if dest.exists():continue
            cap=cv2.VideoCapture(str(base/v['path']));records=[];previous=None;last_rows=[]
            for t in np.arange(0,v['duration_s'],2):
                cap.set(cv2.CAP_PROP_POS_FRAMES,round(t*30));ok,im=cap.read()
                if not ok:continue
                if name=='JotMe测试': rect=(0,200,700,800)
                elif name=='Palabra测试':rect=(430,130,950,1000)
                elif name=='Maestra测试':rect=(920,160,1910,890) if v['id']!='V02' else (450,120,1240,900)
                elif name=='Wordly测试':rect=(0,760,990,1000)
                else:rect=(310,230,1200,600)
                x1,y1,x2,y2=rect;crop=im[y1:y2,x1:x2]
                scale=min(1,780/crop.shape[1]);crop=cv2.resize(crop,None,fx=scale,fy=scale)
                changed=previous is None or float(np.mean(cv2.absdiff(crop,previous)))>.3
                if changed:
                    result,_=engine(crop)
                    rows=[] if result is None else [{'box':(np.asarray(box)/scale+[x1,y1]).tolist(),'text':txt,'confidence':float(score)} for box,txt,score in result]
                    last_rows=rows
                else:rows=last_rows
                previous=crop.copy()
                records.append({'frame':round(t*30),'pts_s':float(t),'items':rows,'reused_unchanged_image':not changed})
                if int(t)%10==0:save(dest.with_suffix('.partial.json'),records)
                if int(t)%20==0: print('OCR',name,v['id'],int(t),flush=True)
            cap.release();save(dest,records)

def assist():
    from scipy.signal import correlate
    current=sys.argv[1] in ['assist2','assist3'];fractional=sys.argv[1]=='assist3';suffix='3' if fractional else ('2' if current else '')
    if current:
        clean,cs=sf.read(ROOT/'outputs/Maestra测试/评测结果_20261103/audio/V01_track1.wav',dtype='float32')
        clean=clean[175595:175595+216064]
    for name in products():
        out=ROOT/'outputs'/name/OUTNAME
        for v in json.loads((out/'manifest.json').read_text(encoding='utf-8')):
            y,sr=sf.read(out/v['tracks'][0]['file'],dtype='float32');res=y.copy()
            matches=json.loads((out/'raw'/f'{v["id"]}_reference_matches.json').read_text(encoding='utf-8'))
            if matches.get('transync_input'):
                r,rs=sf.read(SHARED/'audio/测试音频.wav',dtype='float32');events=matches['transync_input']
                if current:r=clean.copy()
            else:
                r,rs=sf.read(ROOT/'outputs/Maestra测试/analysis_20261102/audio/mix.wav',dtype='float32');r=r[59200:266400];events=matches.get('maestra_source',[])
            details=[]
            for ev in events:
                rough=round(ev['wav_s']*sr);a=max(0,rough-1000);b=min(len(y),rough+3*sr+1000);templ=r[:3*sr]
                c=correlate(y[a:b],templ,mode='valid',method='fft');peak=int(c.argmax());at=peak+a;delta=0.
                rr=r
                if fractional and 0<peak<len(c)-1:
                    from scipy.ndimage import shift
                    delta=float(.5*(c[peak-1]-c[peak+1])/(c[peak-1]-2*c[peak]+c[peak+1]))
                    rr=shift(r,delta,order=3,mode='nearest',prefilter=True);templ=rr[:3*sr]
                seg=y[at:at+len(templ)];gain=float(np.dot(seg,templ)/np.dot(templ,templ));corr=float(np.corrcoef(seg,templ)[0,1])
                count=min(len(rr),len(res)-at);res[at:at+count]-=gain*rr[:count]
                details.append({'wav_s':at/sr,'pts_s':at/sr+v['tracks'][0]['sample0_video_pts_s'],'fractional_sample_shift':delta,'gain':gain,'correlation_first3s':corr,'duration_s':len(r)/sr})
            sf.write(out/'audio'/f'{v["id"]}_target_assist{suffix}.wav',res,sr,subtype='PCM_16')
            save(out/'raw'/f'{v["id"]}_subtraction{suffix}.json',{'method':('Current recording clean source, Maestra V01 WAV 10.9746875 to 24.4786875 s; ' if current else 'Original reference waveform; ')+'lag maximizes 3-second correlation; least-squares gain. Auxiliary transcription/timing only, never primary voiceprint or quality scoring.','events':details})
            print('ASSIST',name,v['id'],details,flush=True)

def asr():
    from faster_whisper import WhisperModel
    model=WhisperModel(str(SHARED/'models/faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=5,num_workers=1)
    for name in products():
        out=ROOT/'outputs'/name/OUTNAME
        for v in json.loads((out/'manifest.json').read_text(encoding='utf-8')):
            suffix='2' if (out/'audio'/f'{v["id"]}_target_assist2.wav').exists() else ''
            y,sr=sf.read(out/'audio'/f'{v["id"]}_target_assist{suffix}.wav',dtype='float32')
            for lang in ['en']:
                dest=out/'raw'/f'{v["id"]}_assist{suffix}_asr.json'
                if dest.exists():continue
                segs,info=model.transcribe(y,language=lang,beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
                rows=[]
                for s in segs:
                    row={'start':s.start,'end':s.end,'text':s.text,'avg_logprob':s.avg_logprob,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in s.words]}
                    rows.append(row);print('ASR',name,v['id'],lang,round(s.start,2),round(s.end,2),s.text,flush=True)
                save(dest,{'model':'faster-whisper-small','language':lang,'sample0_video_pts_s':v['tracks'][0]['sample0_video_pts_s'],'warning':'Forced-language ASR over mixed audio is auxiliary only; Chinese may be hallucinated as English.','segments':rows})

if __name__=='__main__':
    {'prepare':prep,'ocr':ocr,'asr':asr,'assist':assist,'assist2':assist,'assist3':assist}[sys.argv[1]]()
