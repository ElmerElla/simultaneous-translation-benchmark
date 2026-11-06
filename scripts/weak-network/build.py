import os as _publication_os
from pathlib import Path as _PublicationPath
from common import *
import shutil,subprocess,sys
def main():
    compiler=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    if '--reader-only' not in sys.argv:
        result=subprocess.run([str(compiler),'/nologo','/target:exe','/platform:x64','/optimize+','/r:System.Web.Extensions.dll','/r:System.Drawing.dll','/out:'+str(BIN/'NativeCollector.exe'),str(ROOT/'NativeCollector.cs')],capture_output=True,text=True,encoding='utf-8',errors='replace')
        print(result.stdout+result.stderr,flush=True);result.check_returncode()
        shutil.copy2(BIN/'NativeCollector.exe',BIN/'WeakNetICMP.exe')
    result=subprocess.run([str(compiler),'/nologo','/target:exe','/platform:x64','/optimize+','/r:System.Web.Extensions.dll','/r:System.Runtime.Remoting.dll','/out:'+str(BIN/'NetBalancerReadback.exe'),str(ROOT/'NetBalancerReadback.cs')],capture_output=True,text=True,encoding='utf-8',errors='replace')
    print(result.stdout+result.stderr,flush=True);result.check_returncode()
    if not (BIN/'WeakNetProbeCurl.exe').exists():shutil.copy2('C:/Windows/System32/curl.exe',BIN/'WeakNetProbeCurl.exe')
    write(DATA/'build.json',dict(compiler=str(compiler),source_sha256=sha(ROOT/'NativeCollector.cs'),binary_sha256=sha(BIN/'NativeCollector.exe'),built_at=now()))
if __name__=='__main__':main()
