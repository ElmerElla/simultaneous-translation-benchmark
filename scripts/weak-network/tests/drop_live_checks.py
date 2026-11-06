import os as _publication_os
from pathlib import Path as _PublicationPath
"""Real control regression on our own private probe executable only."""
import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import netbalancer as nb
probe=BIN/'WeakNetProbeCurl.exe';checks=[]
def check(label,ok):
    checks.append(dict(name=label,passed=bool(ok)));print(label+': '+('PASS' if ok else 'FAIL'),flush=True)
    if not ok:raise RuntimeError(label)
def file(lease):return DATA/'leases'/(lease['id']+'.json')
if nb.active_leases():raise RuntimeError('已有控制，未启动隔离测试')
if nb.snapshot(probe)['exists']:raise RuntimeError('隔离探针已有配置，未覆盖')
try:
    old=nb.begin_lease(probe,'drop',10,20,3,'内部诊断探针')
    current=nb.snapshot(probe)['config'];check('上行10%下行20%实时回读',current['up_value']==.1 and current['down_value']==.2)
    check('手动恢复丢包配置',nb.restore_lease(file(old)) and not nb.snapshot(probe)['exists'])
    newer=nb.begin_lease(probe,'drop',10,10,8,'内部诊断探针');time.sleep(3.3)
    check('旧计时器不撤销新丢包任务',nb.matches(nb.snapshot(probe)['config'],newer['written']))
    check('新丢包任务恢复',nb.restore_lease(file(newer)))
    conflict=nb.begin_lease(probe,'drop',10,10,10,'内部诊断探针');nb.apply_config(probe,nb.desired('drop',20,10))
    check('丢包外部修改冲突不覆盖',not nb.restore_lease(file(conflict)) and nb.snapshot(probe)['config']['up_value']==.2)
    nb.apply_config(probe,conflict['original']['config']);check('清理本次模拟外部修改',nb.restore_lease(file(conflict)))
    check('隔离探针无残留规则',not nb.snapshot(probe)['exists'])
finally:
    # The simulated external change also belongs exclusively to this test.
    nb.apply_config(probe,nb.desired('delay',0,0))
    for p,l in nb.active_leases():
        if key(l['path'])==key(probe):
            try:nb.restore_lease(p)
            except Exception:pass
    write(LOG/'drop-live-checks.json',dict(at=now(),scope=str(probe),checks=checks,remaining_private_rule=nb.snapshot(probe)['exists'],actual_drop_pct=None,note='只验收配置及恢复，不冒充包级丢弃比例'))
