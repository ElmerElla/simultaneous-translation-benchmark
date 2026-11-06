import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json,hashlib
from pathlib import Path
ROOT=(_PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs');SHARED=ROOT/'Transync测试/analysis_20261102'
sys.path.insert(0,str(SHARED/'deps'))
import numpy as np,soundfile as sf,onnxruntime as ort,kaldi_native_fbank as knf
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
CLIPS={
'JotMe测试':[('N01_tail','V03',31.15,37.5,'正常首次译音未重叠尾段'),('N02_tail','V03',56.0,69.0,'正常重播译音未重叠尾段，含内容重复'),('W04_tail','V01',21.5,37.5,'10%配置译音未重叠尾段')],
'Palabra测试':[('normal_F2_F5','V03',31.0,39.2,'正常录制F2至F5'),('clone_F2_F5','V04',33.5,42.5,'文件标称音色克隆F2至F5'),('W01_full','V02',32.2,45.5,'100ms配置完整译音'),('W04_full','V02',117.5,131.0,'10%配置完整译音')],
'Maestra测试':[('N01_full','V01',26.0,39.0,'首次录次完整译音'),('N02_full','V03',20.7,33.7,'旧正常录次完整译音'),('W01_full','V02',21.0,33.7,'100ms配置完整译音'),('W02_full','V02',56.0,68.7,'Offline撤销后完整译音'),('W04_full','V02',88.3,101.2,'10%配置完整译音')],
'Wordly测试':[('N03_full','V01',67.2,82.8,'开启播音后正常录次完整译音'),('B01_full','V02',26.9,42.5,'弱网录像中No throttling基线完整译音'),('B02_full','V02',59.4,75.1,'弱网录像中第二次No throttling基线译音')],
'Parley测试':[('default_F4_F5','V01',22.05,29.05,'系统音色VV女声F4至F5'),('clone_F4_F5','V03',17.8,23.9,'实时克隆输入声音F4至F5'),('W01_tail','V02',23.1,31.8,'100ms配置未重叠译音尾段'),('W04_tail','V02',95.0,102.3,'10%配置未重叠译音尾段')]}
def main():
 source,rs=sf.read(ROOT/'Maestra测试/评测结果_20261103/audio/V01_track1.wav',dtype='float32');source=source[175595:175595+216064]
 for prod,specs in CLIPS.items():
  out=ROOT/prod/'评测结果_20261103';results=[]
  for label,vid,a,b,note in specs:
   y,sr=sf.read(out/'audio'/f'{vid}_track1.wav',dtype='float32');clip=y[round(a*sr):round(b*sr)]
   sf.write(out/'audio'/f'{label}_clean.wav',clip,sr,subtype='PCM_16')
   hop=160;z=clip[:len(clip)//hop*hop].reshape(-1,hop);rms=np.sqrt((z*z).mean(1));active=np.flatnonzero(rms>10**(-42/20))
   groups=np.split(active,np.where(np.diff(active)>15)[0]+1) if len(active) else []
   ints=[[float(g[0]*.01),float((g[-1]+1)*.01)] for g in groups if len(g)>=5]
   results.append({'id':label,'video':vid,'start_wav_s':a,'end_wav_s':b,'note':note,'path':f'audio/{label}_clean.wav','peak':float(np.abs(clip).max()),'clipping_fraction':float((np.abs(clip)>=.999).mean()),'rms_db':float(20*np.log10(np.sqrt((clip*clip).mean())+1e-12)),'voiced_intervals_relative_s':ints,'gaps_s':[round(ints[i+1][0]-ints[i][1],3) for i in range(len(ints)-1)],'span_s':ints[-1][1]-ints[0][0] if ints else None})
  save(out/'sound_quality.json',results)
  if prod not in ['Palabra测试','Parley测试']:continue
  sf.write(out/'audio/source_S01_clean.wav',source,rs,subtype='PCM_16')
  opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
  model_path=SHARED/'models/campplus_cn_common.onnx';model=ort.InferenceSession(str(model_path),opts,providers=['CPUExecutionProvider'])
  def embedding(y):
   o=knf.FbankOptions();o.frame_opts.dither=0;o.frame_opts.samp_freq=16000;o.frame_opts.snip_edges=True;o.mel_opts.num_bins=80;o.mel_opts.debug_mel=False
   fb=knf.OnlineFbank(o);fb.accept_waveform(16000,y.astype(np.float32));fb.input_finished();f=np.stack([fb.get_frame(i) for i in range(fb.num_frames_ready)]);f-=f.mean(0,keepdims=True)
   return model.run(None,{model.get_inputs()[0].name:f[None].astype(np.float32)})[0][0]
  labels=['source_S01']+(['normal_F2_F5','clone_F2_F5'] if prod=='Palabra测试' else ['default_F4_F5','clone_F4_F5'])
  es={}
  for label in labels:
   y,sr=sf.read(out/'audio'/f'{label}_clean.wav',dtype='float32');e=embedding(y);es[label]=e;np.save(out/'audio'/f'{label}_embedding.npy',e)
  ref=es[labels[0]];scores={label:float(np.dot(ref,es[label])/(np.linalg.norm(ref)*np.linalg.norm(es[label]))) for label in labels[1:]}
  result={'model':'3D-Speaker CAMPPlus iic/speech_campplus_sv_zh-cn_16k-common','dimensions':192,'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),'preprocess':'16kHz mono; 80-bin FBANK; dither=0; mean subtraction; raw cosine; no percent conversion','reference':'audio/source_S01_clean.wav = Maestra cold recording original Chinese WAV 10.9746875–24.4786875 s. Exact same local S01 playback confirmed by waveform matching.','clips':results[:2],'scores':scores,'clone_minus_comparison':scores[labels[2]]-scores[labels[1]],'limit':'Palabra normal vs named clone condition not verified by recorded switch; Parley tail-only semantic comparison, short cross-language samples. No identity threshold or subjective blind listening.'}
  save(out/'speaker_results.json',result);print(prod,json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
