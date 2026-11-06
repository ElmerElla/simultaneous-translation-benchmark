import os as _publication_os
from pathlib import Path as _PublicationPath
"""Real NetBalancer effects, scoped exclusively to our private probe copy."""
import sys,subprocess,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import netbalancer as nb
checks=[];probe=BIN/'WeakNetProbeCurl.exe'
def check(name,ok,details=None):
    checks.append(dict(name=name,passed=bool(ok),details=details));print(name+': '+('PASS' if ok else 'FAIL'),flush=True)
    if not ok:raise RuntimeError(name)
def lease_file(l):return DATA/'leases'/(l['id']+'.json')
def wait_restored(ident,timeout=9):
    limit=time.monotonic()+timeout;p=DATA/'leases'/(ident+'.json')
    while time.monotonic()<limit:
        if read(p,{}).get('state')=='restored':return True
        time.sleep(.15)
    return False
check('隔离探针原规则为空',not nb.snapshot(probe)['exists'])
try:
    first=nb.begin_lease(probe,'delay',70,130,3,'内部诊断探针');actual=nb.snapshot(probe)
    check('上行70下行130方向回读',actual['config']['up_value']==70 and actual['config']['down_value']==130)
    check('独立到时恢复',wait_restored(first['id']) and not nb.snapshot(probe)['exists'])
    old=nb.begin_lease(probe,'outage',0,0,3,'内部诊断探针');check('双向中断回读',nb.snapshot(probe)['config']['up']=='Blocked' and nb.snapshot(probe)['config']['down']=='Blocked')
    check('手动恢复原无规则',nb.restore_lease(lease_file(old)) and not nb.snapshot(probe)['exists'])
    newer=nb.begin_lease(probe,'delay',30,0,7,'内部诊断探针');time.sleep(3.3)
    check('旧计时器不撤销新任务',nb.matches(nb.snapshot(probe)['config'],newer['written']))
    check('新任务手动恢复',nb.restore_lease(lease_file(newer)))
    conflict=nb.begin_lease(probe,'delay',50,50,10,'内部诊断探针')
    changed=nb.desired('delay',0,0);changed.update(down='Low',up='High');nb.apply_config(probe,changed)
    check('外部修改冲突不覆盖',not nb.restore_lease(lease_file(conflict)) and nb.snapshot(probe)['config']['up']=='High')
    # The simulated external edit is also ours, on the private probe only.
    nb.apply_config(probe,conflict['original']['config']);check('冲突自检清理',nb.restore_lease(lease_file(conflict)))
    child=subprocess.run([str(PYTHON),str(ROOT/'tests'/'lease_owner.py')],capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    ident=child.stdout.decode('utf-8-sig').strip();check('父进程已真实退出',child.returncode==0 and len(ident)==32)
    check('父进程退出后独立恢复',wait_restored(ident) and not nb.snapshot(probe)['exists'])
finally:
    # Only the private executable was changed by this file.
    nb.apply_config(probe,nb.desired('delay',0,0))
    for p,l in nb.active_leases():
        if os.path.normcase(l['path'])==os.path.normcase(str(probe)):
            try:nb.restore_lease(p)
            except Exception:pass
    write(LOG/'control-live-checks.json',dict(at=now(),scope=str(probe),checks=checks,remaining_private_rule=nb.snapshot(probe)['exists']))
check('本工具无未完成控制记录',not nb.active_leases())
write(LOG/'control-live-checks.json',dict(at=now(),scope=str(probe),checks=checks,remaining_private_rule=nb.snapshot(probe)['exists']))
