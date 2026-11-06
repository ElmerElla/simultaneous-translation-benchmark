import os as _publication_os
from pathlib import Path as _PublicationPath
"""Independent watchdog, started and acknowledged before a scoped rule write."""
from netbalancer import *
import sys
def main():
    path=Path(sys.argv[1]);lease=read(path);path.with_suffix('.ready').write_text(str(os.getpid()),encoding='utf-8')
    deadline=time.monotonic()+max(0,min(300,lease['expires_epoch_s']-time.time()))
    while time.monotonic()<deadline:
        if read(path,{}).get('state')=='restored':return
        time.sleep(.15)
    for attempt in range(6):
        try:
            if restore_lease(path):return
        except Exception as ex:audit('独立恢复重试',lease=lease['id'],error=str(ex))
        time.sleep(1)
    lease=read(path);lease.update(state='restore_failed',error='独立恢复未确认，请在面板核对并恢复原设置');write(path,lease)
if __name__=='__main__':main()
