import os as _publication_os
from pathlib import Path as _PublicationPath
"""WSL-local authenticated test echo peer; records unique received/sent IDs."""
import sys,socket,selectors,json,time,struct,pathlib,subprocess
nonce=bytes.fromhex(sys.argv[1]);folder=pathlib.Path(sys.argv[2]);folder.mkdir(parents=True,exist_ok=True)
udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);udp.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4*1024*1024);udp.bind(('0.0.0.0',0))
tcp=socket.socket();tcp.bind(('0.0.0.0',0));tcp.listen(4)
sel=selectors.DefaultSelector();sel.register(udp,selectors.EVENT_READ);sel.register(tcp,selectors.EVENT_READ)
def kernel_udp():
    lines=pathlib.Path('/proc/net/snmp').read_text(encoding='utf-8').splitlines()
    for index,line in enumerate(lines[:-1]):
        if line.startswith('Udp:'):return dict(zip(line.split()[1:],map(int,lines[index+1].split()[1:])))
    return {}
runs={};owner=None;stop=False
ip=subprocess.check_output(['hostname','-I'],text=True).split()[0]
print(json.dumps(dict(ready=True,ip=ip,udp_port=udp.getsockname()[1],control_port=tcp.getsockname()[1],receive_buffer=udp.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF))),flush=True)
while not stop:
    for key,_ in sel.select(1):
        if key.fileobj is udp:
            data,addr=udp.recvfrom(2048)
            if len(data)!=128 or data[:4]!=b'WN2P' or data[4:20]!=nonce or addr[0]!=owner:continue
            run,seq=struct.unpack_from('<II',data,20);r=runs.get(run)
            if not r or seq>=r['expected']:continue
            if seq in r['received']:r['duplicates']+=1
            else:r['received'][seq]=time.monotonic_ns()
            try:
                if udp.sendto(data,addr)==len(data):r['sent'].add(seq)
                else:r['send_errors']+=1
            except OSError:r['send_errors']+=1
        else:
            conn,addr=tcp.accept();conn.settimeout(3)
            with conn:
                try:
                    raw=b''
                    while not raw.endswith(b'\n') and len(raw)<8192:
                        part=conn.recv(8192)
                        if not part:break
                        raw+=part
                    req=json.loads(raw)
                    if req.get('token')!=nonce.hex() or owner not in (None,addr[0]):raise ValueError('Unauthorized test controller')
                    owner=addr[0];op=req['op'];ident=req.get('run')
                    if op=='begin':
                        if ident in runs:raise ValueError('Run IDs cannot be reused')
                        runs[ident]=dict(expected=req['count'],received={},sent=set(),duplicates=0,send_errors=0,kernel_before=kernel_udp());out=dict(started=True)
                    elif op=='stats':
                        r=runs[ident];out=dict(run=ident,expected=r['expected'],received_sequence=sorted(r['received']),sent_sequence=sorted(r['sent']),unique_received=len(r['received']),unique_sent=len(r['sent']),duplicates=r['duplicates'],send_errors=r['send_errors'],kernel_udp_before=r['kernel_before'],kernel_udp_after=kernel_udp())
                        detail=dict(out,receive_monotonic_ns=r['received']);(folder/('peer-'+str(ident)+'.json')).write_text(json.dumps(detail,indent=2),encoding='utf-8')
                    elif op=='stop':stop=True;out=dict(stopped=True)
                    else:raise ValueError('Unsupported operation')
                    conn.sendall(json.dumps(out).encode()+b'\n')
                except Exception as ex:conn.sendall(json.dumps(dict(error=str(ex))).encode()+b'\n')
udp.close();tcp.close()
