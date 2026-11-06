import os as _publication_os
from pathlib import Path as _PublicationPath
from common import *
import subprocess,urllib.request,webbrowser,sys
def launch():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def alive():
        try:
            with opener.open('http://127.0.0.1:'+str(PORT)+'/api/health',timeout=1) as r:return json.load(r).get('app_id')==APP_ID
        except Exception:return False
    if not alive():
        if not (BIN/'NativeCollector.exe').exists():subprocess.run([str(PYTHON),str(ROOT/'build.py')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        log=(LOG/'server.log').open('a',encoding='utf-8')
        child=subprocess.Popen([str(PYTHON),str(ROOT/'server.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);log.close()
        for _ in range(100):
            if alive():break
            if child.poll() is not None:raise RuntimeError('面板启动失败，请查看 logs/server.log')
            time.sleep(.1)
        else:raise RuntimeError('面板启动超时')
    session=read(DATA/'session.json',{})
    if not session.get('token'):raise RuntimeError('启动认证未准备好')
    # Fragment is removed by the page and is never sent as an HTTP URL or log.
    webbrowser.open('http://127.0.0.1:'+str(PORT)+'/#session='+session['token']+('&selftest=1' if '--selftest' in sys.argv else ''))
if __name__=='__main__':
    try:launch()
    except Exception as ex:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,str(ex),'弱网面板 v2',0x10)
