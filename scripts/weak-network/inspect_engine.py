import os as _publication_os
from pathlib import Path as _PublicationPath
"""Bootstrap the vendor XML mapping using only the owned curl copy."""
from netbalancer import *
import sys,shutil
TARGET=BIN/'WeakNetProbeCurl.exe'
def main():
    if '--recover-only' in sys.argv:
        time.sleep(12)
        cli(['settings','priorities','edit',str(TARGET),'Normal','Normal'])
        return
    if not TARGET.exists():shutil.copy2('C:/Windows/System32/curl.exe',TARGET)
    before=snapshot(TARGET);assert not before['exists'],'Bootstrap target already has a rule; no write allowed'
    with (LOG/'schema-probe.log').open('w',encoding='utf-8') as probe_log:
        probe=subprocess.Popen([str(TARGET),'--noproxy','*','--max-time','15','--limit-rate','8192','--output','NUL','--silent','--show-error','https://speed.cloudflare.com/__down?bytes=65536'],stdout=probe_log,stderr=probe_log,creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(1.5)
    with (LOG/'schema-recovery.log').open('w',encoding='utf-8') as log:
        subprocess.Popen([str(PYTHON),str(Path(__file__)),'--recover-only'],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        print(cli(['settings','priorities','edit',str(TARGET),'Delayed','Delayed','100','100','0','0','false']))
        found=[]
        for _ in range(50):
            found=records(TARGET)
            if found:break
            time.sleep(.1)
        write(DATA/'schema-observation.json',dict(before=before,records=found))
        print(json.dumps(found,ensure_ascii=False,indent=2),flush=True)
        raw=[dict(file=p.name,xml=p.read_text('utf-8-sig')) for p in NB_DATA.glob('Priorities*.xml') if len(ET.fromstring(p.read_text('utf-8-sig')))>0]
        write(DATA/'schema-raw.json',raw);print(json.dumps(raw,ensure_ascii=False,indent=2),flush=True)
    finally:
        print(cli(['settings','priorities','edit',str(TARGET),'Normal','Normal']))
        if probe.poll() is None:probe.terminate();probe.wait(5)
if __name__=='__main__':main()
