import os as _publication_os
from pathlib import Path as _PublicationPath
"""Offline evidence extraction. Source videos and source workbooks are read-only.
All text is UTF-8. Local pre-existing audio/OCR models are reused; no network calls.
"""
from pathlib import Path
import sys, json, subprocess, hashlib, zipfile, xml.etree.ElementTree as ET

ROOT = _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))
BASE = ROOT / 'outputs/讯飞同传测试'
OUT = BASE / '评测结果_20261104'
SHARED = ROOT / 'outputs/Transync测试/analysis_20261102'
# Bundled runtime lacks the audio/OCR packages. Reuse already installed local tools.
sys.path.insert(0, str(SHARED / 'deps'))
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def run(args):
    return subprocess.check_output([str(x) for x in args], stderr=subprocess.PIPE)

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def read_xlsx(path):
    ns = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as z:
        ss = []
        if 'xl/sharedStrings.xml' in z.namelist():
            ss = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels = {x.attrib['Id']:x.attrib['Target'].lstrip('/') for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        sheets=[]
        for sh in ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',ns):
            rid=sh.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target=rels[rid]
            if not target.startswith('xl/'):target='xl/'+target
            xml=ET.fromstring(z.read(target));cells={}
            for cell in xml.findall('.//m:sheetData/m:row/m:c',ns):
                value=cell.find('m:v',ns);typ=cell.attrib.get('t');val=value.text if value is not None else None
                if typ=='s' and val is not None:val=ss[int(val)]
                elif typ=='inlineStr':val=''.join(cell.find('m:is',ns).itertext())
                formula=cell.find('m:f',ns)
                cells[cell.attrib['r']]={'value':val,'formula':formula.text if formula is not None else None,'style':cell.attrib.get('s')}
            sheets.append({'name':sh.attrib['name'],'part':target,'cells':cells,'merges':[x.attrib['ref'] for x in xml.findall('m:mergeCells/m:mergeCell',ns)]})
        return {'path':str(path),'sha256':sha(path),'sheets':sheets,'parts':z.namelist()}

def prepare():
    for sub in ['audio','frames','raw','_support']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    books={name:read_xlsx(path) for name,path in {
        'comparison':ROOT/'测试结论.xlsx',
        'reference':ROOT/'outputs/Transync测试/outputs/评测结果_20261102/Transync五项测试结果.xlsx'
    }.items()}
    save(OUT/'raw/source_books.json',books)
    for name,book in books.items():
        print('WORKBOOK',name,[(s['name'],len(s['cells'])) for s in book['sheets']],flush=True)
        if name=='comparison':
            for s in book['sheets']:
                print(json.dumps({k:v['value'] for k,v in s['cells'].items()},ensure_ascii=False),flush=True)
    manifest=[]
    for i,video in enumerate(sorted(BASE.glob('*.mkv'))):
        key=f'V{i+1:02}'
        probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',video]))
        save(OUT/'raw'/f'{key}_probe.json',probe)
        pts=json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=pts_time,best_effort_timestamp_time','-of','json',video]))
        save(OUT/'raw'/f'{key}_video_pts.json',pts)
        tracks=[]
        for st in probe['streams']:
            if st['codec_type']!='audio':continue
            dest=OUT/'audio'/f'{key}_track{st["index"]}.wav'
            if not dest.exists():run(['ffmpeg','-v','error','-y','-i',video,'-map',f'0:{st["index"]}','-ac','1','-ar','16000','-c:a','pcm_s16le',dest])
            y,sr=sf.read(dest,dtype='int16')
            tracks.append({'stream':st['index'],'title':st.get('tags',{}).get('title'),'file':str(dest.relative_to(OUT)),'pcm_sha256':hashlib.sha256(y.tobytes()).hexdigest(),'samples':len(y),'sr':sr,'sample0_pts_s':float(st.get('start_time',0))})
        row={'id':key,'path':str(video.relative_to(BASE)),'sha256':sha(video),'duration_s':float(probe['format']['duration']),'tracks':tracks,'tracks_identical':len({t['pcm_sha256'] for t in tracks})==1}
        manifest.append(row)
        import cv2
        cap=cv2.VideoCapture(str(video));images=[]
        for t in np.arange(0,row['duration_s'],10):
            cap.set(cv2.CAP_PROP_POS_FRAMES,round(t*30));ok,frame=cap.read()
            if not ok:continue
            im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.thumbnail((960,540))
            dest=OUT/'frames'/f'{key}_overview_{int(t):03}.jpg';im.save(dest,quality=88)
            images.append((float(t),im.copy()))
        cap.release()
        for start in range(0,len(images),8):
            canvas=Image.new('RGB',(1920,575*4),'#eeeeee');draw=ImageDraw.Draw(canvas)
            for j,(t,im) in enumerate(images[start:start+8]):
                x=(j%2)*960;y=(j//2)*575
                draw.text((x+12,y+6),f'{key}  PTS {t:.1f} s',fill='black',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22))
                canvas.paste(im,(x,y+32))
            canvas.save(OUT/'frames'/f'{key}_overview_contact_{start//8+1}.jpg',quality=91)
        y,sr=sf.read(OUT/tracks[0]['file']);hop=160;z=y[:len(y)//hop*hop].reshape(-1,hop)
        db=20*np.log10(np.sqrt((z*z).mean(1))+1e-12);np.savez_compressed(OUT/'audio'/f'{key}_energy.npz',db=db)
        save(OUT/'raw'/f'{key}_energy.json',{'hop_s':.01,'thresholds_dbfs':[-55,-50,-42,-35],'sample0_pts_s':tracks[0]['sample0_pts_s']})
        print('VIDEO',json.dumps(row,ensure_ascii=False),flush=True)
    save(OUT/'manifest.json',manifest)

def audio():
    from faster_whisper import WhisperModel
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    summary=[]
    for v in manifest:
        for tr in v['tracks']:
            y,sr=sf.read(OUT/tr['file'],dtype='float32');hop=160
            z=y[:len(y)//hop*hop].reshape(-1,hop);db=20*np.log10(np.sqrt((z*z).mean(1))+1e-12)
            active=np.flatnonzero(db>-42)
            groups=np.split(active,np.where(np.diff(active)>35)[0]+1) if len(active) else []
            intervals=[[round(g[0]*.01+tr['sample0_pts_s'],3),round((g[-1]+1)*.01+tr['sample0_pts_s'],3)] for g in groups if len(g)>8]
            row={'stream':tr['stream'],'title':tr['title'],'peak':float(np.abs(y).max()),'active_intervals_pts_s':intervals,'silence_fraction':float(np.mean(y==0))}
            summary.append(row);print('AUDIO',json.dumps(row,ensure_ascii=False),flush=True)
    save(OUT/'raw/audio_summary.json',summary)
    model=WhisperModel(str(SHARED/'models/faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=5,num_workers=1)
    for v in manifest:
        for stream,lang in [(2,'zh'),(3,'en')]:
            tr=next(t for t in v['tracks'] if t['stream']==stream)
            dest=OUT/'raw'/f'{v["id"]}_track{stream}_asr.json'
            if dest.exists():continue
            y,sr=sf.read(OUT/tr['file'],dtype='float32')
            segments,info=model.transcribe(y,language=lang,beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
            rows=[]
            for seg in segments:
                row={'start':seg.start,'end':seg.end,'text':seg.text,'avg_logprob':seg.avg_logprob,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in seg.words]}
                rows.append(row);print('ASR',stream,round(seg.start,2),round(seg.end,2),seg.text,flush=True)
                save(dest.with_suffix('.partial.json'),rows)
            save(dest,{'model':'faster-whisper-small','lang':lang,'track':stream,'sample0_pts_s':tr['sample0_pts_s'],'note':'ASR is auxiliary, acoustic timing and screenshot review are separate.','segments':rows})

def ocr():
    import cv2
    from rapidocr_onnxruntime import RapidOCR
    cv2.setNumThreads(1)
    engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,rec_batch_num=1,use_cls=False,det_limit_type='max',det_limit_side_len=1100)
    for v in json.loads((OUT/'manifest.json').read_text(encoding='utf-8')):
        cap=cv2.VideoCapture(str(BASE/v['path']));partial=OUT/'raw'/f'{v["id"]}_ocr.partial.json'
        rows=json.loads(partial.read_text(encoding='utf-8')) if partial.exists() else []
        start=rows[-1]['pts_s']+2 if rows else 0
        for t in np.arange(start,v['duration_s'],2):
            cap.set(cv2.CAP_PROP_POS_FRAMES,round(t*30));ok,im=cap.read()
            if not ok:continue
            result,_=engine(im)
            rows.append({'frame':round(t*30),'pts_s':float(t),'items':[{'box':np.asarray(box).tolist(),'text':txt,'confidence':float(conf)} for box,txt,conf in (result or [])]})
            if int(t)%20==0:
                save(OUT/'raw'/f'{v["id"]}_ocr.partial.json',rows);print('OCR',v['id'],int(t),flush=True)
        cap.release();save(OUT/'raw'/f'{v["id"]}_ocr.json',rows)

def target():
    from faster_whisper import WhisperModel
    model=WhisperModel(str(SHARED/'models/faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=4,num_workers=1)
    y,sr=sf.read(OUT/'audio/V01_track1.wav',dtype='float32')
    segs,info=model.transcribe(y,language='en',beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    rows=[]
    for seg in segs:
        row={'start':seg.start,'end':seg.end,'text':seg.text,'avg_logprob':seg.avg_logprob,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in seg.words]}
        rows.append(row);save(OUT/'raw/V01_translation_asr.partial.json',rows)
        print('EN',round(seg.start,2),round(seg.end,2),seg.text,flush=True)
    save(OUT/'raw/V01_translation_asr.json',{'model':'faster-whisper-small','track':1,'lang':'en','sample0_pts_s':-.021,'segments':rows,'note':'Track title is mix but acoustic evidence shows predominantly English translation. No source cancellation used.'})

def evidence():
    import cv2
    from scipy.signal import correlate,find_peaks
    src,sr=sf.read(OUT/'audio/V01_track2.wav',dtype='float32')
    other,_=sf.read(OUT/'audio/V01_track3.wav',dtype='float32')
    en,_=sf.read(OUT/'audio/V01_track1.wav',dtype='float32')
    template=src[round(35*sr):round(48.5*sr)]
    def matches(y):
        a=y[::4].astype('float64');r=template[::4].astype('float64')
        c=correlate(a,r,mode='valid',method='fft');cs=np.r_[0.,np.cumsum(a*a)]
        energy=np.maximum(0.,cs[len(r):]-cs[:-len(r)]);refenergy=np.sum(r*r)
        c=np.divide(c,np.sqrt(energy*refenergy),out=np.zeros_like(c),where=energy>refenergy*.005)
        c=np.clip(c,-1.,1.)
        peaks,_=find_peaks(c,height=.3,distance=4000*10)
        return [{'template_wav_s':float(i/4000),'template_pts_s':float(i/4000-.021),'correlation':float(c[i])} for i in peaks]
    save(OUT/'raw/track_provenance.json',{'template':'track2 WAV35.0..48.5s','track2_matches':matches(src),'track3_matches':matches(other),'track1_matches':matches(en),'note':'Names are not accepted as provenance. Track2/3 source matching plus ASR, track1 translation ASR and source/target non-overlap establish roles. Independent path latency calibration is unavailable.'})
    if '--provenance-only' in sys.argv:
        print('PROVENANCE',json.dumps({'source':matches(src),'other':matches(other),'target_source_matches':matches(en)}),flush=True)
        return
    video=next(BASE.glob('*.mkv'));cap=cv2.VideoCapture(str(video))
    # Full-size frames retain configuration object, active state, subtitles and controls.
    times=list(range(0,37,2))+list(range(86,174,2))+list(range(184,216,2))+list(range(234,282,2))+[48,54,62,74,84,112,120,142,182,232,240,260,272,280,304,308]
    index=[]
    for t in sorted(set(times)):
        cap.set(cv2.CAP_PROP_POS_FRAMES,round(t*30));ok,im=cap.read()
        if not ok:continue
        dest=OUT/'frames'/f'V01_detail_{t:03}.png';cv2.imencode('.png',im)[1].tofile(str(dest));index.append({'pts_s':t,'path':str(dest.relative_to(OUT))})
    cap.release();save(OUT/'raw/detail_frames.json',index)
    print('SOURCE MATCHES',json.dumps(matches(src)),flush=True)
    print('TRACK3 MATCHES',json.dumps(matches(other)),flush=True)
    print('TRACK1 SOURCE MATCHES',json.dumps(matches(en)),flush=True)

if __name__=='__main__':
    {'prepare':prepare,'audio':audio,'ocr':ocr,'target':target,'evidence':evidence}[sys.argv[1]]()
