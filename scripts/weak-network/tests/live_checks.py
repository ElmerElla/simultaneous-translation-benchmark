import os as _publication_os
from pathlib import Path as _PublicationPath
"""Read-only live API checks and isolated diagnostic requests. No app shaping."""
import sys,urllib.request,urllib.error,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import collector_client,netbalancer as nb
token=read(DATA/'session.json')['token'];origin='http://127.0.0.1:'+str(PORT);opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));checks=[]
def api(path,body=None,auth=True,origin_value=origin):
    headers={'Content-Type':'application/json','Origin':origin_value}
    if auth:headers['X-Session-Token']=token
    req=urllib.request.Request(origin+path,None if body is None else json.dumps(body).encode(),headers)
    try:
        with opener.open(req,timeout=10) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as ex:return ex.code,json.load(ex)
def check(name,condition,detail=None):
    checks.append(dict(name=name,passed=bool(condition),detail=detail));print(name+': '+('PASS' if condition else 'FAIL'),flush=True)
status,data=api('/api/programs');check('程序目录可读',status==200 and len(data['programs'])>10,len(data.get('programs',[])))
check('缺权限流量为null',all(a['upload'] is None or a['upload']['value'] is None for a in data['programs']) if not data['system']['admin'] else True)
check('真实程序控制已启用',data['control']['gate']['available'],data['control']['gate']['reason'])
check('匿名访问拒绝',api('/api/programs',auth=False)[0]==403)
check('跨站请求拒绝',api('/api/session',{},origin_value='https://example.invalid')[0]==403)
check('旧控制接口拒绝',api('/api/control',{})[0]==400)
check('任意路径控制拒绝',api('/api/control',dict(app_id='C:\\Windows\\not-discovered.exe'))[0]==400)
check('无运行中的控制记录',not data['control']['active'])
status,export=api('/api/export');check('JSON导出无启动令牌',status==200 and token not in json.dumps(export))
start=time.perf_counter();snap=collector_client.query(dict(op='snapshot'));elapsed=(time.perf_counter()-start)*1000
check('本机采集IPC工作',len(snap['processes'])>10,dict(ms=elapsed,programs=len(snap['processes']),connections=len(snap['connections']),etw=snap['etw']['status']))
# Diagnostics target is our panel, not a business program request. Selected app
# only supplies a stable catalogue identity; no controls are applied.
app=next(a for a in data['programs'] if a.get('path') and a['path'].lower()==str(PYTHON).lower())
status,job=api('/api/diagnose',dict(app_id=app['id'],target='http://127.0.0.1:'+str(PORT)))
check('独立诊断可启动',status==200)
limit=time.monotonic()+45
while time.monotonic()<limit:
    _,job=api('/api/diagnostic?app_id='+app['id'])
    if job and job['state']!='running':break
    time.sleep(.5)
check('三次新连接',len(job.get('https',[]))==3)
check('20次ICMP样本保留',len((job.get('icmp') or {}).get('samples',[]))==20)
check('诊断来源不冒充程序流量',job['policy']['mode']=='direct' and not job['policy']['protocol_coverage_confirmed'])
write(LOG/'live-checks.json',dict(at=now(),checks=checks,diagnostic_id=job['id']))
sys.exit(0 if all(c['passed'] for c in checks) else 1)
