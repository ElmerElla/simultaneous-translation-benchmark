import os as _publication_os
from pathlib import Path as _PublicationPath
"""Manual offline-to-Codex self-test, scoped to our copied curl only."""
from common import *
import netbalancer as nb
import subprocess,statistics,sys,uuid
from diagnostics import target_url,curl_once
def restore_probe(path,original):
    nb.apply_config(path,original['config'])
    clean=nb.wait_config(path,original['config'])
    if clean['exists']!=original['exists']:raise RuntimeError('隔离探针的原配置条目未精确恢复')
    return clean

def check_drop(path,original):
    cases=[]
    for up,down in ((10,10),(0,10),(10,0),(100,100)):
        expected=nb.desired('drop',up,down)
        nb.apply_config(path,expected);actual=nb.wait_config(path,expected)
        for row in actual['records']:
            if any(float(row['fields'][tag])!=0 for tag in ('DownloadDelay','UploadDelay','DownloadDelayJitter','UploadDelayJitter')):
                raise RuntimeError('丢包配置中检测到非零延迟，拒绝开放')
        cases.append(dict(upstream_drop_pct=up,downstream_drop_pct=down,actual=actual))
        restore_probe(path,original)
    manual=nb.begin_lease(path,'drop',10,10,10,'内部诊断探针',require_gate=False)
    if not nb.restore_lease(DATA/'leases'/(manual['id']+'.json')):raise RuntimeError('丢包手动恢复未确认')
    timed=nb.begin_lease(path,'drop',10,10,2,'内部诊断探针',require_gate=False)
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        if read(DATA/'leases'/(timed['id']+'.json'))['state']=='restored':break
        time.sleep(.1)
    else:raise RuntimeError('丢包独立定时恢复未确认')
    if nb.snapshot(path)['exists']:raise RuntimeError('丢包测试结束后仍有隔离规则')
    return dict(cases=cases,manual_recovery=True,timed_recovery=True,actual_drop_pct=None,scope='配置回读及恢复，未测包级实际丢弃比例')

def verify(url):
    import msvcrt
    # One bootstrap owner across CLI and browser invocations.
    with (DATA/'selftest.lock').open('a+b') as lock:
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise RuntimeError('另一个隔离自检正在运行')
        try:return _verify(url)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

def _verify(url):
    url,_=target_url(url);path=BIN/'WeakNetProbeCurl.exe'
    if nb.active_leases():raise RuntimeError('请先恢复当前控制任务')
    before=nb.snapshot(path)
    if before['exists']:raise RuntimeError('隔离探针已有规则，未覆盖它')
    gate=dict(passed=False,started_at=now(),**nb.fingerprints(),scope=str(path),reason='控制自检进行中',modes={m:dict(passed=False,reason='尚未完成验收') for m in ('delay','outage','drop')})
    write(DATA/'engine-verification.json',gate)
    nonce=uuid.uuid4().hex;guard=DATA/'selftest-guard.json'
    write(guard,dict(nonce=nonce,state='armed',original=before,expires_epoch_s=time.time()+90))
    with (LOG/'selftest-recovery.log').open('w',encoding='utf-8') as out:
        child=subprocess.Popen([str(PYTHON),str(ROOT/'selftest.py'),'--cleanup-guard',nonce],stdout=out,stderr=out,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+3
    while not (DATA/('selftest-'+nonce+'.ready')).exists():
        if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('隔离自检恢复进程未就绪，未施加损伤')
        time.sleep(.03)
    try:
        try:
            gate['baseline']=[curl_once(url) for _ in range(2)]
            baseline_ok=all(x['exit_code']==0 for x in gate['baseline'])
        except Exception as ex:baseline_ok=False;gate['baseline_error']=str(ex)
        for mode in ('delay','outage','drop'):
            result=gate['modes'][mode]
            try:
                if mode=='drop':result['validation']=check_drop(path,before)
                else:
                    if not baseline_ok:raise RuntimeError('直连基线未成功，未验证该模式的网络效果')
                    config=nb.desired(mode,100,100) if mode=='delay' else nb.desired(mode,0,0)
                    nb.apply_config(path,config);result['actual']=nb.wait_config(path,config)
                    if mode=='delay':
                        gate['delayed']=[curl_once(url) for _ in range(2)]
                        b=[r['phases']['tcp']['value'] for r in gate['baseline'] if r['phases']['tcp']['status']=='valid']
                        d=[r['phases']['tcp']['value'] for r in gate['delayed'] if r['phases']['tcp']['status']=='valid']
                        if not b or not d or statistics.median(d)-statistics.median(b)<100:raise RuntimeError('未验证到附加延迟效果')
                    else:
                        gate['blocked']=curl_once(url)
                        if gate['blocked']['exit_code'] not in (7,28):raise RuntimeError('未验证到预期连接失败或超时')
                result.update(passed=True,reason=None)
            except Exception as ex:result.update(passed=False,reason=str(ex))
            finally:
                # A mode failure cannot leave a rule behind or contaminate the next.
                restore_probe(path,before)
                for file,lease in nb.active_leases():
                    if key(lease['path'])==key(path) and not nb.restore_lease(file):raise RuntimeError('隔离租约恢复尚未确认')
    except Exception as ex:gate['reason']=str(ex)
    finally:
        try:
            clean=restore_probe(path,before)
            for file,lease in nb.active_leases():
                if key(lease['path'])==key(path) and not nb.restore_lease(file):raise RuntimeError('隔离租约恢复尚未确认')
            gate['restoration']=dict(exact_original_entry_absence=not clean['exists'],config=clean['config'])
            gate['passed']=any(r['passed'] for r in gate['modes'].values())
            gate['reason']=None if all(r['passed'] for r in gate['modes'].values()) else '部分模式未通过，请查看各模式结果'
            write(guard,dict(nonce=nonce,state='finished'))
        except Exception as ex:
            gate.update(passed=False,reason='隔离探针恢复未确认：'+str(ex))
        gate['finished_at']=now();write(DATA/'engine-verification.json',gate);write(LOG/('engine-selftest-'+str(time.time_ns())+'.json'),gate)
    return gate
if __name__=='__main__':
    if '--cleanup-guard' in sys.argv:
        nonce=sys.argv[-1];(DATA/('selftest-'+nonce+'.ready')).write_text(str(os.getpid()),encoding='utf-8')
        while True:
            g=read(DATA/'selftest-guard.json',{})
            if g.get('nonce')!=nonce or g.get('state')!='armed':break
            if time.time()>=g['expires_epoch_s']:
                nb.apply_config(BIN/'WeakNetProbeCurl.exe',g['original']['config']);write(DATA/'selftest-guard.json',dict(nonce=nonce,state='recovered'));break
            time.sleep(.2)
    else:print(json.dumps(verify(sys.argv[1] if len(sys.argv)>1 else 'https://example.com/'),ensure_ascii=False,indent=2))
