import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,json
from pathlib import Path
ROOT=(_PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs');sys.path.insert(0,str(ROOT/'Transync测试/analysis_20261102/deps'))
import numpy as np,soundfile as sf
from PIL import Image,ImageDraw,ImageFont
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
for prod in ['JotMe测试','Palabra测试','Maestra测试','Wordly测试','Parley测试']:
 out=ROOT/prod/'评测结果_20261103';rows=json.loads((out/'completion_candidates.json').read_text(encoding='utf-8'));tiles=[]
 for r in rows:
  if r.get('audio_end_pts_s') is None:continue
  a,b=r['audio_tail_search_wav_s'];y,sr=sf.read(out/'audio'/f'{r["video"]}_track1.wav');hop=80;z=y[round(a*sr):round(b*sr)];z=z[:len(z)//hop*hop].reshape(-1,hop);db=20*np.log10(np.sqrt((z*z).mean(1))+1e-12)
  im=Image.new('RGB',(900,260),'white');d=ImageDraw.Draw(im);d.text((5,5),f'{prod} {r["scene"]} raw mix, WAV {a}-{b}s; end PTS {r["audio_end_pts_s"]:.3f}s',font=font,fill='black')
  xx=lambda t:65+(t-a)/(b-a)*820; yy=lambda v:220-(max(-85,min(0,v))+85)/85*170
  for v in [-70,-50,-42,-35,-20,0]:d.line((65,yy(v),885,yy(v)),fill='#ccdddd');d.text((5,yy(v)-7),str(v),font=font,fill='black')
  d.line([(xx(a+i*.005),yy(float(v))) for i,v in enumerate(db)],fill='#25639c',width=2)
  ex=xx(r['audio_end_pts_s']+.021);d.line((ex,40,ex,223),fill='#cc2222',width=2)
  d.text((60,235),f'{a:.2f}',font=font,fill='black');d.text((820,235),f'{b:.2f}',font=font,fill='black');tiles.append(im)
 canvas=Image.new('RGB',(1800,260*((len(tiles)+1)//2)),'#ddd')
 for i,im in enumerate(tiles):canvas.paste(im,((i%2)*900,(i//2)*260))
 canvas.save(out/'frames/译音末响波形复核.png');print(prod,len(tiles),flush=True)
