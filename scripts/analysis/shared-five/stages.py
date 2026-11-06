import os as _publication_os
from pathlib import Path as _PublicationPath
"""Persist visually reviewed startup stages and terminal-output observations."""
import json,csv
from pathlib import Path
ROOT=(_PublicationPath(_publication_os.environ.get('BENCHMARK_WORKSPACE', _PublicationPath(__file__).resolve().parents[3]))/'outputs')
DATA={
'JotMe测试':('V03',[
 ('程序窗口出现',2,4,'2秒仍为桌面，4秒为JotMe Loading；点击启动本身未逐帧定点。','cold'),
 ('主界面出现',6,8,'6秒仍Loading，8秒主界面已显示；不等于会话连接完成。','cold'),
 ('会话可接收输入',14,15,'14秒显示正在准备，15秒准备提示消失且暂停/停止控制可见。','cold_ready')],
 '程序加载约2～8秒区间；会话就绪在录像14～15秒之间，输入17.5秒才开始。'),
'Palabra测试':('V01',[
 ('程序窗口出现',3,6,'3秒桌面、6秒白色程序窗口；12秒仍白屏，15秒主界面Start可见。','cold'),
 ('主界面出现',12,15,'Start只是可请求连接；18～30秒仍Please wait，期间有连接耗时较长提示。','cold'),
 ('会话可接收输入',30,31,'30秒Please wait，31秒显示Speak和空历史栏。','cold_ready')],
 '主界面在12～15秒出现；会话就绪在30～31秒之间，输入32.0秒才开始。'),
'Maestra测试':('V01',[
 ('浏览器打开',1,2,'1秒桌面，2秒Chrome用户选择；不是Maestra页面启动完成。','cold'),
 ('产品主页显示',5,6,'5秒地址栏转入产品、页面仍Google；6秒Maestra主页可见。','cold'),
 ('会话连接中',8,9,'8秒仍配置首页，9秒为连接中。','cold'),
 ('会话可接收输入',10,10.5,'10秒连接中，10.5秒显示您现在可以开始说话了。','cold_ready')],
 '浏览器1～2秒打开；产品主页5～6秒可见；会话就绪10～10.5秒，输入11.0秒开始。'),
'Wordly测试':('V01',[
 ('程序/浏览器打开',None,None,'录像0秒两端浏览器已打开，只记录加入会话过程，无法测程序打开耗时。','cold'),
 ('讲话端加入',2,4,'2秒仍Join，4秒已显示会话工具栏；尚未完成麦克风路由选择。','cold'),
 ('听众端加入',4,6,'4秒仍Attend入口/加载，6秒已进入英文听众页，初期播音关闭。','cold'),
 ('输入路由配置完毕的可见上界',8,10,'8秒麦克风设置弹窗，10秒弹窗关闭；输入声卡选择与页面连接是不同阶段。','cold')],
 '浏览器打开时间缺失；讲话端2～4秒、听众端4～6秒加入，路由配置8～10秒完成；初期播音关闭。'),
'Parley测试':('V01',[
 ('程序窗口出现',3,4,'3秒桌面，4秒Parley透明加载窗口出现。','cold'),
 ('主界面出现',4,5,'4秒加载、5秒准备好了就开始配置页可见；不等于会话已连接。','cold'),
 ('会话准备中',5,6,'5秒开始入口，6秒正在准备双向同传。','cold'),
 ('会话可接收输入',7,8,'7秒仍准备中，8秒显示正在聆听与计时。','cold')],
 '程序窗口3～4秒出现，主界面4～5秒；会话就绪7～8秒之间，输入8.3秒开始。')}
def main():
 for prod,(vid,stages,summary) in DATA.items():
  out=ROOT/prod/'评测结果_20261103';rows=[]
  for label,lo,hi,note,tag in stages:
   paths=[]
   for t in [lo,hi]:
    if t is not None:
     p=f'frames/{vid}_{tag}_{round(t*30):05d}.png';assert (out/p).exists();paths.append(p)
   if not paths:paths=[f'frames/{vid}_cold_00000.png']
   rows.append({'stage':label,'video':vid,'after_pts_s':lo,'by_pts_s':hi,'note':note,'evidence':paths})
  (out/'startup_stages.json').write_text(json.dumps({'summary':summary,'interval_semantics':'状态发生于前一截图之后、后一截图之前/当时；不是精确点击时间或单独可比较的纯网络连接耗时。','stages':rows},ensure_ascii=False,indent=2),encoding='utf-8')
  with (out/'启动阶段表.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(['阶段','视频','前一时刻秒','后一时刻秒','判断与限制','证据']);w.writerows([[r['stage'],vid,r['after_pts_s'],r['by_pts_s'],r['note'],';'.join(r['evidence'])] for r in rows])
  complete=json.loads((out/'completion_candidates.json').read_text(encoding='utf-8'))
  for r in complete:
   if r.get('status') in ['adjacent_frame_candidate','whole_history_block_appears_at_once']:r['review']='已视觉复核尾句前后相邻帧；尾词首次显全不代表以后不再修改。'
   else:r['review']='当前录像不足以确认本轮字幕尾句完成。'
  (out/'output_completion.json').write_text(json.dumps(complete,ensure_ascii=False,indent=2),encoding='utf-8')
  with (out/'输出完成事件表.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(['场景','视频','源音秒','尾句首次显全秒','译音末响秒','尾句显全等待秒','末响等待秒','判断与限制','截图'])
   for r in complete:
    s=r.get('subtitle_tail_pts_s');a=r.get('audio_end_pts_s');src=r['source_pts_s']
    w.writerow([r['scene'],r['video'],src,s,a,None if s is None else s-src,None if a is None else a-src,r.get('note','')+' '+r['review'],';'.join(r.get('screenshots',[]))])
  print(prod,'startup',len(rows),'completion',len(complete),flush=True)
if __name__=='__main__':main()
