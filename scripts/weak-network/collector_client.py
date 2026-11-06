import os as _publication_os
from pathlib import Path as _PublicationPath
from common import *
import re,subprocess,ctypes
PIPE_LOCK=threading.Lock()
def query(data,timeout=2):
    info=read(DATA/'collector-info.json',{})
    name=info.get('pipe','')
    if not re.fullmatch(r'WeakNetV2-[a-f0-9]{24}',name):raise RuntimeError('采集进程尚未就绪')
    full='\\\\.\\pipe\\'+name
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.WaitNamedPipeW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint]
    with PIPE_LOCK:
        if not k.WaitNamedPipeW(full,int(timeout*1000)):raise RuntimeError('无法连接本机采集进程')
        with open(full,'r+b',buffering=0) as pipe:
            import msvcrt
            k.PeekNamedPipe.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint),ctypes.c_void_p]
            pipe.write((json.dumps(data)+'\n').encode('utf-8'));chunks=[];size=0;deadline=time.monotonic()+max(timeout,3)
            handle=msvcrt.get_osfhandle(pipe.fileno())
            while True:
                available=ctypes.c_uint()
                if not k.PeekNamedPipe(handle,None,0,None,ctypes.byref(available),None):raise RuntimeError('采集连接已经关闭')
                if available.value:
                    chunk=pipe.read(min(65536,available.value));chunks.append(chunk);size+=len(chunk)
                    if size>16*1024*1024:raise RuntimeError('采集响应过大')
                    if b'\n' in chunk:break
                elif time.monotonic()>deadline:raise RuntimeError('采集响应超时')
                else:time.sleep(.01)
            line=b''.join(chunks).split(b'\n',1)[0]
        result=json.loads(line.decode('utf-8-sig'))
        if result.get('error'):raise RuntimeError(result['error'])
        return result
def start_normal():
    try:query(dict(op='snapshot'));return None
    except Exception:pass
    log=(LOG/('collector-'+str(time.time_ns())+'.log')).open('w',encoding='utf-8')
    p=subprocess.Popen([str(BIN/'NativeCollector.exe')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);log.close()
    for _ in range(50):
        try:
            value=query(dict(op='snapshot'))
            if 'processes' in value:return p
        except Exception:pass
        if p.poll() is not None:raise RuntimeError('Windows采集进程启动失败')
        time.sleep(.1)
    raise RuntimeError('Windows采集进程准备超时')
def start_admin():
    try:query(dict(op='stop'))
    except Exception:pass
    time.sleep(2)
    shell=ctypes.WinDLL('shell32');shell.ShellExecuteW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_int];shell.ShellExecuteW.restype=ctypes.c_void_p
    result=shell.ShellExecuteW(None,'runas',str(BIN/'NativeCollector.exe'),None,str(ROOT),0)
    if result is None or result<=32:raise RuntimeError('完整采集需要你在Windows授权窗口中确认')
if __name__=='__main__':
    import sys
    if '--admin' in sys.argv:start_admin()
    else:start_normal();print('采集进程已就绪')
