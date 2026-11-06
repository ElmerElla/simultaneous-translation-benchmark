import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,uuid,subprocess,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import netbalancer as nb
def rows():
    p=subprocess.run([str(BIN/'InspectVendor.exe'),'--ipc','100663834'],capture_output=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError(p.stdout.decode('utf-8',errors='replace'))
    return [r for r in json.loads(p.stdout.decode('utf-8-sig')) if os.path.normcase(r['Key'])==os.path.normcase(str(BIN/'WeakNetProbeCurl.exe'))]
before=rows()
if before:raise RuntimeError('Private probe has a pre-existing priority; unchanged')
nonce=uuid.uuid4().hex;original=dict(exists=False,config=nb.desired('delay',0,0))
write(DATA/'selftest-guard.json',dict(nonce=nonce,state='armed',original=original,expires_epoch_s=time.time()+90))
guard=subprocess.Popen([str(PYTHON),str(ROOT/'selftest.py'),'--cleanup-guard',nonce],creationflags=subprocess.CREATE_NO_WINDOW)
deadline=time.monotonic()+3
while not (DATA/('selftest-'+nonce+'.ready')).exists():
    if guard.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Guard not ready')
    time.sleep(.02)
result=dict(at=now(),before=before)
try:
    nb.apply_config(BIN/'WeakNetProbeCurl.exe',nb.desired('delay',70,130));result['delayed']=rows()
finally:
    nb.apply_config(BIN/'WeakNetProbeCurl.exe',original['config']);result['after']=rows()
    if not result['after']:write(DATA/'selftest-guard.json',dict(nonce=nonce,state='finished'))
    write(LOG/'live-reader-validation.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))
