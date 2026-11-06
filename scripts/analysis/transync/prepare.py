import os as _publication_os
from pathlib import Path as _PublicationPath
import os, sys, json, subprocess, hashlib
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=_PublicationPath(_publication_os.environ.get('BENCHMARK_TRANSYNC_ANALYSIS', _PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs/Transync测试/analysis_20261102')).parent
OUT=ROOT/'analysis_20261102'
def run(args):
    return subprocess.run(args,check=True,capture_output=True).stdout
def save_json(p,data):
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=[]
for key,name in [('normal','冷启动、正常翻译、关闭音色克隆翻译.mkv'),('network','延迟100ms、中断10s测试.mkv')]:
    src=ROOT/'outputs'/name
    meta=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(src)]))
    save_json(OUT/f'{key}_probe.json',meta)
    for kind in ['v:0','a:1','a:2']:
        frames=json.loads(run(['ffprobe','-v','error','-select_streams',kind,'-show_frames','-show_entries','frame=pts_time,best_effort_timestamp_time,pkt_dts_time,nb_samples,key_frame','-of','json',str(src)]))
        save_json(OUT/f'{key}_{kind.replace(":","_")}_frame_pts.json',frames)
    packets=json.loads(run(['ffprobe','-v','error','-show_packets','-show_entries','packet=stream_index,pts_time,dts_time,duration_time,flags,side_data_list','-of','json',str(src)]))
    save_json(OUT/f'{key}_packet_pts.json',packets)
    for idx,label in [(1,'mix'),(2,'source'),(3,'translated')]:
        dest=OUT/'audio'/f'{key}_{label}.wav'
        run(['ffmpeg','-v','error','-y','-i',str(src),'-map',f'0:{idx}','-ac','1','-ar','16000','-c:a','pcm_s16le',str(dest)])
    frames_dir=OUT/'frames'/key
    frames_dir.mkdir(exist_ok=True)
    run(['ffmpeg','-v','error','-y','-i',str(src),'-vf',"select=not(mod(n\\,150)),scale=640:-1",'-fps_mode','vfr',str(frames_dir/'overview_%03d.jpg')])
    images=list(sorted(frames_dir.glob('overview_*.jpg')))
    for batch in range(0,len(images),12):
        canvas=Image.new('RGB',(1280,390*6),'#dddddd')
        draw=ImageDraw.Draw(canvas)
        for j,p in enumerate(images[batch:batch+12]):
            x=(j%2)*640; y=(j//2)*390
            canvas.paste(Image.open(p),(x,y+25))
            draw.text((x+8,y+5),f'{key}   t={(batch+j)*5:.3f}s',fill='black')
        canvas.save(OUT/'frames'/f'{key}_contact_{batch//12+1}.jpg')
    manifest.append({'id':key,'path':str(src.relative_to(ROOT)),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'duration':meta['format']['duration']})
for p in (ROOT/'inputs').glob('*.m4a'):
    meta=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
    save_json(OUT/f'{p.stem}_probe.json',meta)
    run(['ffmpeg','-v','error','-y','-i',str(p),'-ac','1','-ar','16000','-c:a','pcm_s16le',str(OUT/'audio'/f'{p.stem}.wav')])
    manifest.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'duration':meta['format']['duration']})
save_json(OUT/'manifest.json',manifest)
print(json.dumps(manifest,ensure_ascii=False),flush=True)
