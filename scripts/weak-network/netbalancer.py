import os as _publication_os
from pathlib import Path as _PublicationPath
"""Application-path-only NetBalancer adapter. No global settings operations."""
from common import *
import subprocess, xml.etree.ElementTree as ET

_service_cache=(0,None)
def service_status():
    """Read-only Service Control Manager checks; never start/stop services."""
    global _service_cache
    if time.monotonic()-_service_cache[0]<5:return _service_cache[1]
    import ctypes
    a=ctypes.WinDLL('advapi32',use_last_error=True);a.OpenSCManagerW.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint];a.OpenSCManagerW.restype=ctypes.c_void_p;a.OpenServiceW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];a.OpenServiceW.restype=ctypes.c_void_p;a.QueryServiceStatus.argtypes=[ctypes.c_void_p,ctypes.c_void_p];a.CloseServiceHandle.argtypes=[ctypes.c_void_p]
    result={};scm=a.OpenSCManagerW(None,None,1)
    if not scm:return dict(available=False,reason='无法读取NetBalancer服务状态')
    try:
        for name in ('NetBalancerService','nbdrv'):
            handle=a.OpenServiceW(scm,name,4)
            if not handle:result[name]=None;continue
            try:
                row=(ctypes.c_uint*7)();result[name]=row[1] if a.QueryServiceStatus(handle,ctypes.byref(row)) else None
            finally:a.CloseServiceHandle(handle)
    finally:a.CloseServiceHandle(scm)
    out=dict(available=all(v==4 for v in result.values()),states=result,reason=None if all(v==4 for v in result.values()) else 'NetBalancer服务或驱动未运行，或缺少查询权限')
    _service_cache=(time.monotonic(),out);return out

def cli(args,timeout=5):
    if not NB.is_file():raise RuntimeError('未安装NetBalancer本机命令工具')
    result=subprocess.run([str(NB),*map(str,args)],capture_output=True,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    out=result.stdout.decode('utf-8',errors='replace')+result.stderr.decode('utf-8',errors='replace')
    if result.returncode:raise RuntimeError('NetBalancer命令失败，代码 '+str(result.returncode))
    return out

def disk_records(path):
    path=os.path.normcase(os.path.abspath(path));found=[]
    for file in NB_DATA.glob('Priorities*.xml'):
        tree=ET.fromstring(file.read_text('utf-8-sig'))
        for node in tree:
            leaves={child.tag.split('}')[-1]:child.text for child in node.iter() if len(child)==0}
            if any(text and os.path.normcase(text)==path for text in leaves.values()):
                found.append(dict(file=str(file),fields=leaves,xml=ET.tostring(node,encoding='unicode')))
    return found

def fingerprints():
    return dict(nb_sha256=sha(NB),adapter_sha256=sha(__file__),reader_sha256=sha(BIN/'NetBalancerReadback.exe'),core_sha256=sha(NB.parent/'SeriousBit.NetBalancer.Core.dll'))

def verified(gate):
    try:return gate.get('passed') and all(gate.get(k)==v for k,v in fingerprints().items())
    except OSError:return False

def mode_verified(gate,mode):
    modes=gate.get('modes')
    if modes is None:return bool(gate.get('passed')) and mode in ('delay','outage')
    return bool(modes.get(mode,{}).get('passed'))

def lease_parameters(lease):
    """Human units; vendor drop fractions must never be truncated to integers."""
    scale=100 if lease['mode']=='drop' else 1
    return tuple(int(round(float(lease['written'][side+'_value'])*scale)) for side in ('up','down'))

def live_priorities(path=None):
    args=[str(BIN/'NetBalancerReadback.exe')]+([str(path)] if path is not None else [])
    result=subprocess.run(args,capture_output=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
    try:data=json.loads(result.stdout.decode('utf-8-sig'))
    except Exception:raise RuntimeError('NetBalancer实时配置读取失败')
    if result.returncode or data.get('status')!='valid':raise RuntimeError(data.get('error','NetBalancer实时配置不可用'))
    return data

def records(path):
    data=live_priorities(path)
    return [dict(fields=f,source=data['source'],sampled_at=data['sampled_at']) for f in data['records']]

def snapshot(path):
    rows=records(path)
    if not rows:return dict(exists=False,config=dict(down='Normal',up='Normal',down_value=0,up_value=0,down_jitter=0,up_jitter=0,per_connection=False))
    # The concrete vendor field mapping is enabled only after the isolated test.
    mapping=dict(down='DownloadPriority',up='UploadPriority',down_jitter='DownloadDelayJitter',up_jitter='UploadDelayJitter',per_connection='PerConnectionLimits')
    configurations=[]
    for row in rows:
        f=row['fields'];c={}
        for name,tag in mapping.items():
            if tag not in f:raise RuntimeError('NetBalancer配置字段变化，停止写入')
            value=f[tag]
            c[name]=value.lower()=='true' if name=='per_connection' else value if name in ('down','up') else float(value)
        for side,prefix in [('down','Download'),('up','Upload')]:
            tag=prefix+{'Delayed':'Delay','Limited':'Limit','Dropped':'DropRate'}.get(c[side],'Delay')
            c[side+'_value']=float(f[tag])
        configurations.append(c)
    if any(c!=configurations[0] for c in configurations):raise RuntimeError('发现多份不一致的程序配置，停止写入')
    return dict(exists=True,config=configurations[0],records=rows)

def apply_config(path,c):
    if c['down'] not in ('Normal','High','Low','Ignored','Limited','Delayed','Dropped','Blocked') or c['up'] not in ('Normal','High','Low','Ignored','Limited','Delayed','Dropped','Blocked'):
        raise RuntimeError('不支持精确恢复此类原配置')
    return cli(['settings','priorities','edit',path,c['down'],c['up'],c['down_value'],c['up_value'],c.get('down_jitter',0),c.get('up_jitter',0),str(c.get('per_connection',False)).lower()])

def desired(mode,up=100,down=100):
    if mode not in ('delay','outage','drop'):raise ValueError('未知损伤模式')
    if mode=='drop':
        if any(type(v) is not int or not 0<=v<=100 for v in (up,down)):raise ValueError('丢包概率必须为0～100的整数百分比')
        return dict(down='Dropped' if down else 'Normal',up='Dropped' if up else 'Normal',down_value=down/100,up_value=up/100,down_jitter=0,up_jitter=0,per_connection=False)
    return dict(down='Blocked' if mode=='outage' else 'Delayed' if down else 'Normal',up='Blocked' if mode=='outage' else 'Delayed' if up else 'Normal',down_value=down if mode=='delay' else 0,up_value=up if mode=='delay' else 0,down_jitter=0,up_jitter=0,per_connection=False)

def matches(a,b):
    # Values for Normal/Blocked are dormant vendor fields; preserve them in
    # snapshots, but do not require the service to rewrite unused values.
    for side in ('down','up'):
        if a[side]!=b[side]:return False
        if a[side] in ('Delayed','Dropped','Limited') and abs(float(a[side+'_value'])-float(b[side+'_value']))>1e-9:return False
        if a[side]=='Delayed' and float(a.get(side+'_jitter',0))!=float(b.get(side+'_jitter',0)):return False
    return a.get('per_connection',False)==b.get('per_connection',False)

def wait_config(path,expected,timeout=5):
    limit=time.monotonic()+timeout;last=None
    while time.monotonic()<limit:
        last=snapshot(path)
        if matches(last['config'],expected):return last
        time.sleep(.1)
    raise RuntimeError('未能从NetBalancer本机服务回读预期设置')

def restore_lease(path,force=False):
    import msvcrt
    lease_path=Path(path);lockfile=lease_path.with_suffix('.lock')
    with lockfile.open('a+b') as lock:
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:return False
        try:
            lease=read(lease_path)
            if not lease or lease.get('state')=='restored':return True
            current=snapshot(lease['path'])
            if lease.get('actual') and current['exists']:
                actual_fields=[r['fields'] for r in lease['actual'].get('records',[])]
                current_fields=[r['fields'] for r in current.get('records',[])]
                original_fields=[r['fields'] for r in lease['original'].get('records',[])]
                if current_fields not in (actual_fields,original_fields):
                    lease.update(state='conflict',error='完整程序配置已被外部修改，未覆盖');write(lease_path,lease);return False
            if not matches(current['config'],lease['written']) and not matches(current['config'],lease['original']['config']):
                lease.update(state='conflict',error='程序配置已被其他工具修改，未覆盖外部设置');write(lease_path,lease);return False
            apply_config(lease['path'],lease['original']['config'])
            after=wait_config(lease['path'],lease['original']['config'])
            if not lease['original']['exists'] and after['exists']:
                raise RuntimeError('原配置项不存在，但恢复后仍保留条目；精确恢复未通过')
            lease.update(state='restored',restored_at=now(),error=None);write(lease_path,lease)
            audit('恢复原程序设置',app=Path(lease['path']).name,lease=lease['id'])
            return True
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

def begin_lease(path,mode,up,down,seconds,label=None,require_gate=True):
    import uuid
    if require_gate:
        gate=read(DATA/'engine-verification.json',{})
        if not verified(gate) or not mode_verified(gate,mode):raise RuntimeError('该控制模式尚未通过当前版本的隔离自检')
    original=snapshot(path)
    if original['exists']:raise RuntimeError('此程序已有优先级规则，当前适配器尚未验证其无损恢复；未修改')
    ident=uuid.uuid4().hex
    lease=dict(id=ident,path=str(Path(path).resolve()),label=label or Path(path).name,mode=mode,original=original,written=desired(mode,up,down),duration_s=seconds,expires_epoch_s=time.time()+seconds,state='armed',created_at=now())
    file=DATA/'leases'/(ident+'.json');write(file,lease)
    log=(LOG/('recovery-'+ident+'.log')).open('w',encoding='utf-8')
    child=subprocess.Popen([str(PYTHON),str(ROOT/'recovery.py'),str(file)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);log.close()
    # Recovery must have started before any program configuration is changed.
    deadline=time.monotonic()+3
    while time.monotonic()<deadline and not file.with_suffix('.ready').exists():
        if child.poll() is not None:raise RuntimeError('独立恢复进程未启动，未修改程序设置')
        time.sleep(.03)
    if not file.with_suffix('.ready').exists():raise RuntimeError('恢复进程准备超时，未修改程序设置')
    try:
        import msvcrt
        # Serialize the initial write/readback against a short-duration watchdog.
        with file.with_suffix('.lock').open('a+b') as rule_lock:
            if rule_lock.tell()==0:rule_lock.write(b'0');rule_lock.flush()
            rule_lock.seek(0);msvcrt.locking(rule_lock.fileno(),msvcrt.LK_LOCK,1)
            try:
                if read(file)['state']!='armed':raise RuntimeError('控制任务已结束，未应用过期设置')
                apply_config(path,lease['written']);actual=wait_config(path,lease['written']);lease.update(state='active',actual=actual,recovery_pid=child.pid);write(file,lease)
            finally:rule_lock.seek(0);msvcrt.locking(rule_lock.fileno(),msvcrt.LK_UNLCK,1)
        parameters=dict(upstream_drop_pct=up,downstream_drop_pct=down) if mode=='drop' else dict(up_ms=up,down_ms=down) if mode=='delay' else {}
        audit('应用程序弱网设置',app=lease['label'],mode=mode,duration_s=seconds,lease=ident,**parameters)
        return lease
    except Exception:
        restore_lease(file)
        raise

def active_leases():
    return [(p,read(p)) for p in (DATA/'leases').glob('*.json') if read(p,{}).get('state')!='restored']
