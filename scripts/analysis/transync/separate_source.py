import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json
from pathlib import Path
BASE=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102'));sys.path.insert(0,str(BASE/'deps'))
import numpy as np,soundfile as sf
from scipy.signal import correlate
from scipy.ndimage import shift
sr=16000
y,_=sf.read(BASE/'audio'/'normal_mix.wav',dtype='float32')
ref=y[round(15.1*sr):round(28.1*sr)]
result=[]
for key,t in [('normal',59.57),('normal',95.47),('network',16.52),('network',52.96),('network',68.50)]:
    sig,_=sf.read(BASE/'audio'/f'{key}_mix.wav',dtype='float32')
    start=round((t-.05)*sr);segment=sig[start:round((t+4.05)*sr)]
    c=correlate(segment,ref[:4*sr],mode='valid',method='fft')
    peak=int(np.argmax(c));delta=.5*(c[peak-1]-c[peak+1])/(c[peak-1]-2*c[peak]+c[peak+1]) if 0<peak<len(c)-1 else 0
    offset=start+peak
    # Fractional sample interpolation accounts for independent recorder clocks.
    ref_shift=shift(ref,delta,order=3,mode='nearest',prefilter=True)
    target=sig[offset:offset+len(ref)]
    gain=float(np.dot(target[:4*sr],ref_shift[:4*sr])/np.dot(ref_shift[:4*sr],ref_shift[:4*sr]))
    residual=target-gain*ref_shift
    corr=float(np.corrcoef(target[:4*sr],ref_shift[:4*sr])[0,1])
    path=BASE/'audio'/f'residual_{key}_{t:.2f}.wav';sf.write(path,residual,sr,subtype='PCM_16')
    hop=160;z=residual[:len(residual)//hop*hop].reshape(-1,hop);rms=np.sqrt(np.mean(z*z,axis=1))
    db=20*np.log10(rms+1e-12)
    rows=[]
    for th in [-55,-50,-45,-40,-35]:
        inds=np.flatnonzero(db>th);groups=np.split(inds,np.where(np.diff(inds)>20)[0]+1)
        rows.append({'threshold':th,'intervals_video_pts':[[round(float(offset/sr+g[0]*.01-.021),3),round(float(offset/sr+(g[-1]+1)*.01-.021),3)] for g in groups if len(g)>=5]})
    result.append({'key':key,'test':t,'offset_wav':offset/sr,'fractional_samples':float(delta),'gain':gain,'input_correlation':corr,'rms_first4sec':float(np.sqrt(np.mean(residual[:4*sr]**2))),'residual_intervals':rows})
(BASE/'source_subtraction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
