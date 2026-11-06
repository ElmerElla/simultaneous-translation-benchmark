import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json,hashlib
from pathlib import Path
BASE=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102'));sys.path.insert(0,str(BASE/'deps'))
import numpy as np,soundfile as sf,onnxruntime as ort,kaldi_native_fbank as knf
opts=ort.SessionOptions();opts.intra_op_num_threads=3;opts.inter_op_num_threads=1
model_path=BASE/'models'/'campplus_cn_common.onnx'
model=ort.InferenceSession(str(model_path),opts,providers=['CPUExecutionProvider'])
meta=model.get_modelmeta().custom_metadata_map
def embed(y):
    fopts=knf.FbankOptions();fopts.frame_opts.dither=0;fopts.frame_opts.samp_freq=16000;fopts.frame_opts.snip_edges=True;fopts.mel_opts.num_bins=80;fopts.mel_opts.debug_mel=False
    fb=knf.OnlineFbank(fopts);fb.accept_waveform(16000,y.astype(np.float32));fb.input_finished()
    f=np.stack([fb.get_frame(i) for i in range(fb.num_frames_ready)]);f-=f.mean(0,keepdims=True)
    emb=model.run(None,{model.get_inputs()[0].name:f[np.newaxis].astype(np.float32)})[0][0]
    return emb
specs=[('S01_input','测试音频',0,13.504),('clone_reference','声音克隆音频',0,22.336),('clone_cold_S01','normal_mix',33.3,49),('default_S01','normal_mix',111.5,124.6),('clone_warm_tail','normal_mix',73.3,81.3)]
embs={};rows=[]
for label,name,start,end in specs:
    y,sr=sf.read(BASE/'audio'/f'{name}.wav',dtype='float32');assert sr==16000
    y=y[round(start*sr):round(end*sr)]
    # Trim leading/trailing silence at peak-relative threshold, retaining internal pauses.
    hop=160;z=y[:len(y)//hop*hop].reshape(-1,hop);rms=np.sqrt(np.mean(z*z,axis=1));active=np.flatnonzero(rms>max(float(np.max(rms))*.01,1e-5))
    a=max(0,(int(active[0])-3)*hop);b=min(len(y),(int(active[-1])+4)*hop);y=y[a:b]
    emb=embed(y);embs[label]=emb
    np.save(BASE/'audio'/f'{label}_campplus_embedding.npy',emb)
    sf.write(BASE/'audio'/f'{label}_speaker_clip.wav',y,sr,subtype='PCM_16')
    rows.append({'id':label,'file':name+'.wav','start_wav':start+a/sr,'end_wav':start+b/sr,'duration':len(y)/sr,'embedding_dimension':len(emb),'sample_peak':float(np.max(np.abs(y)))})
def cos(a,b):return float(np.dot(embs[a],embs[b])/(np.linalg.norm(embs[a])*np.linalg.norm(embs[b])))
pairs=[{'reference':a,'comparison':b,'cosine':cos(a,b)} for a,b in [('S01_input','clone_cold_S01'),('S01_input','default_S01'),('S01_input','clone_warm_tail'),('clone_reference','S01_input'),('clone_reference','clone_cold_S01'),('clone_reference','default_S01')]]
data={'model_metadata':meta,'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),'model_download':'https://huggingface.co/csukuangfj/speaker-embedding-models/resolve/0743f301363dec56491a490f6d6cbc9d67f9a3bf/3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx','method':'16kHz mono; float [-1,1]; Kaldi 80-bin fbank, dither=0, global mean subtraction; full-utterance embedding; raw cosine, no percentage mapping','clips':rows,'pairs':pairs}
(BASE/'speaker_results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(data,ensure_ascii=False,indent=2),flush=True)
