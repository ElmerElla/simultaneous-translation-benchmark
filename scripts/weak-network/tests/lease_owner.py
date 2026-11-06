import os as _publication_os
from pathlib import Path as _PublicationPath
"""Isolated owner used to verify recovery after a real parent process exit."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import netbalancer as nb
lease=nb.begin_lease(BIN/'WeakNetProbeCurl.exe','outage',0,0,3,'内部诊断探针')
print(lease['id'],flush=True)
os._exit(0)
