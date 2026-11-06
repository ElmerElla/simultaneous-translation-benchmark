import os as _publication_os
from pathlib import Path as _PublicationPath
"""Two-ended local-WSL UDP loss verification, isolated executable paths only."""
import sys,json,socket,subprocess,time,uuid,math,datetime,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import netbalancer as nb

def wilson(lost,n):
    if not n:return None
    z=1.95996398454;p=lost/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0.0,100*(mid-half)),min(100.0,100*(mid+half))]

def summarize(client,peer):
    sent={i for i,t in enumerate(client['sent_qpc']) if t};replies={i for i,t in enumerate(client['received_qpc']) if t}
    got=set(peer['received_sequence']);echoed=set(peer['sent_sequence'])
    def loss(a,b):
        missing=sorted(a-b);n=len(a)
        return dict(sent=n,received=len(a&b),lost=len(missing),loss_pct=len(missing)*100/n if n else None,ci95_pct=wilson(len(missing),n),missing_sequence=missing)
    kernel_errors={k:peer.get('kernel_udp_after',{}).get(k,0)-peer.get('kernel_udp_before',{}).get(k,0) for k in ('InErrors','RcvbufErrors','SndbufErrors')}
    return dict(upstream=loss(sent,got),downstream=loss(echoed,replies),round_trip=loss(sent,replies),unexpected_peer_sequence=sorted(got-sent),unexpected_reply_sequence=sorted(replies-echoed),send_errors=client['send_errors'],receive_errors=client['receive_errors'],peer_send_errors=peer['send_errors'],duplicates_client=client['duplicates'],duplicates_peer=peer['duplicates'],kernel_udp_error_delta=kernel_errors)

class Validation:
    def __init__(self):
        self.nonce=uuid.uuid4().hex;self.folder=LOG/('packet-loss-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));self.folder.mkdir();self.runs=[];self.ident=0;self.peer=None;self.info=None;self.error=None
        self.probe=BIN/'WeakNetUdpProbe.exe';self.control=BIN/'WeakNetUdpControl.exe';self.active=None
    def start(self):
        if nb.active_leases():raise RuntimeError('已有控制任务，未开始测试')
        if nb.snapshot(self.probe)['exists'] or nb.snapshot(self.control)['exists']:raise RuntimeError('隔离程序有原规则，未覆盖')
        def linux(path):return '/mnt/'+path.drive[0].lower()+str(path)[2:].replace('\\','/')
        err=(self.folder/'wsl-peer-stderr.log').open('wb')
        self.peer=subprocess.Popen(['wsl.exe','-d','Ubuntu','--exec','python3','-u',linux(ROOT/'tests'/'udp_sequence_peer.py'),self.nonce,linux(self.folder)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=err);err.close()
        with concurrent.futures.ThreadPoolExecutor() as pool:self.info=json.loads(pool.submit(self.peer.stdout.readline).result(timeout=15).decode('utf-8'))
        self.command('begin',run=0,count=1) # authenticate controller without sending traffic
        print('Peer ready: '+self.info['ip'],flush=True)
    def command(self,op,**values):
        with socket.create_connection((self.info['ip'],self.info['control_port']),timeout=5) as s:
            s.settimeout(5);s.sendall((json.dumps(dict(op=op,token=self.nonce,**values))+'\n').encode());raw=b''
            while not raw.endswith(b'\n'):
                part=s.recv(65536)
                if not part:break
                raw+=part
            result=json.loads(raw)
        if result.get('error'):raise RuntimeError(result['error'])
        return result
    def spawn(self,exe,count,pps,drain=2000):
        self.ident+=1;ident=self.ident;output=self.folder/('client-'+str(ident)+'.json')
        p=subprocess.Popen([str(exe),self.info['ip'],str(self.info['udp_port']),self.nonce,str(ident),str(count),str(pps),str(output),str(drain)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        with concurrent.futures.ThreadPoolExecutor() as pool:ready=json.loads(pool.submit(p.stdout.readline).result(timeout=5).decode('utf-8'))
        self.command('begin',run=ident,count=count)
        return dict(process=p,id=ident,output=output,ready=ready)
    def run(self,name,up=0,down=0,count=4000,pps=400,negative=False):
        main=self.spawn(self.probe,count,pps);other=self.spawn(self.control,count,pps) if negative else None
        lease=None;actual=None;started=now();row=None
        try:
            if up or down:
                lease=nb.begin_lease(self.probe,'drop',up,down,min(300,int(count/pps)+20),'隔离UDP丢包验证')
                self.active=DATA/'leases'/(lease['id']+'.json');actual=nb.snapshot(self.probe)
            main['process'].stdin.write(b'GO\n');main['process'].stdin.flush()
            if other:other['process'].stdin.write(b'GO\n');other['process'].stdin.flush()
            for item in [main]+([other] if other else []):
                p=item['process'];p.wait(timeout=count/pps+8)
                if p.returncode:raise RuntimeError(p.stderr.read().decode('utf-8',errors='replace'))
            client=read(main['output']);peer=self.command('stats',run=main['id']);data=summarize(client,peer)
            row=dict(name=name,run_id=main['id'],configured_up_pct=up,configured_down_pct=down,started_at=started,finished_at=now(),client_ready=main['ready'],actual_config=actual,summary=data)
            if other:row['negative_control']=summarize(read(other['output']),self.command('stats',run=other['id']))
            if lease:
                row['rule_still_active']=read(self.active)['state']=='active' and nb.matches(nb.snapshot(self.probe)['config'],lease['written'])
                if not row['rule_still_active']:raise RuntimeError('规则提前结束，该组无效')
            data['valid']=not any([data['unexpected_peer_sequence'],data['unexpected_reply_sequence'],data['send_errors'],data['receive_errors'],data['peer_send_errors'],*data['kernel_udp_error_delta'].values()])
            self.runs.append(row);write(self.folder/'result.json',self.report())
            if not data['valid']:raise RuntimeError('发送/接收或内核缓冲出现错误，该组测量无效')
            print(name+': '+json.dumps({k:data[k]['loss_pct'] for k in ('upstream','downstream','round_trip')})+' %',flush=True)
            return row
        finally:
            for item in [main]+([other] if other else []):
                if item['process'].poll() is None:item['process'].kill();item['process'].wait(3)
            if lease:
                if not nb.restore_lease(self.active):raise RuntimeError('隔离规则恢复未确认')
                self.active=None
    def report(self):return dict(created_at=now(),scope='Windows隔离进程→WSL2受控UDP端点；不代表Transync业务或公网链路',peer=self.info,runs=self.runs,error=self.error,payload_bytes=128,application_retransmissions=0,source_sha256=sha(ROOT/'tests'/'UdpSequenceProbe.cs'),harness_sha256=sha(__file__),peer_sha256=sha(ROOT/'tests'/'udp_sequence_peer.py'),probe_sha256=sha(self.probe),control_sha256=sha(self.control))
    def close(self):
        if self.active:
            try:nb.restore_lease(self.active)
            except Exception as ex:self.error=(self.error or '')+';恢复错误:'+str(ex)
        if self.info:
            try:self.command('stop')
            except Exception:pass
        if self.peer:
            try:self.peer.wait(5)
            except subprocess.TimeoutExpired:self.peer.terminate();self.peer.wait(5)
        report=self.report();report['private_rule_absent']=not nb.snapshot(self.probe)['exists'];report['control_rule_absent']=not nb.snapshot(self.control)['exists'];write(self.folder/'result.json',report)

def main():
    v=Validation()
    try:
        v.start();r=v.run('calibration_N0',count=200,pps=200)
        if r['summary']['round_trip']['lost']:raise RuntimeError('无损校准已有数据报缺失，停止正式验证')
        r=v.run('calibration_U100',up=100,count=200,pps=200)
        if r['summary']['upstream']['lost']!=200:raise RuntimeError('100%上行丢包未覆盖WSL路径，停止10%测量')
        r=v.run('calibration_D100',down=100,count=200,pps=200)
        if r['summary']['downstream']['lost']!=200:raise RuntimeError('100%下行丢包未覆盖WSL路径，停止10%测量')
        if '--calibrate-only' not in sys.argv:
            v.run('N0_before',negative=True)
            for repeat in range(1,4):
                v.run('U10_repeat_'+str(repeat),up=10,negative=True)
                v.run('D10_repeat_'+str(repeat),down=10,negative=True)
            v.run('B10_both',up=10,down=10,negative=True);v.run('N0_recovery',negative=True)
    except Exception as ex:v.error=str(ex);print('INVALID: '+str(ex),flush=True)
    finally:v.close();print('Evidence: '+str(v.folder),flush=True)
    return 1 if v.error else 0
if __name__=='__main__':sys.exit(main())
