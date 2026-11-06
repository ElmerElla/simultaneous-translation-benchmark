import os as _publication_os
from pathlib import Path as _PublicationPath
from common import *
import collector_client,ctypes
if __name__=='__main__':
    try:collector_client.start_admin()
    except Exception as ex:
        try:collector_client.start_normal()
        except Exception:pass
        ctypes.windll.user32.MessageBoxW(None,str(ex)+'\n已保留普通权限监控。','管理员采集',0x30)
