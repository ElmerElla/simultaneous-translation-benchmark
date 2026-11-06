import os as _publication_os
from pathlib import Path as _PublicationPath
from pathlib import Path
import datetime, hashlib, json, os, threading, time
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
LOG=ROOT/'logs'
BIN=ROOT/'bin'
PORT=18492
APP_ID='local-weak-network-panel-v2'
NB=_PublicationPath(_publication_os.environ.get('NETBALANCER_CMD', 'C:/Program Files/NetBalancer/nbcmd.exe'))
NB_DATA=Path('C:/ProgramData/SeriousBit/NetBalancer')
PYTHON=_PublicationPath(_publication_os.environ.get('BENCHMARK_PYTHON', __import__('sys').executable))
LOCK=threading.RLock()
for folder in (DATA,LOG,BIN):folder.mkdir(parents=True,exist_ok=True)
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def key(path):return hashlib.sha256(os.path.normcase(os.path.abspath(path)).encode('utf-8')).hexdigest()[:24]
def read(path,default=None):
    try:return json.loads(Path(path).read_text('utf-8-sig'))
    except FileNotFoundError:return default
def write(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp')
    with LOCK:
        tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        for attempt in range(30):
            try:os.replace(tmp,p);return
            except PermissionError:
                if attempt==29:raise
                time.sleep(.02)
def audit(event,**values):
    with LOCK,(LOG/'actions.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(at=now(),event=event,**values),ensure_ascii=False)+'\n')
