import os as _publication_os
from pathlib import Path as _PublicationPath
from common import *
import concurrent.futures,statistics,subprocess,urllib.parse,uuid,ipaddress,socket
import netbalancer as nb
from catalog import metric

def target_url(text):
    if not isinstance(text,str) or len(text)>512:raise ValueError('请输入域名或HTTP/HTTPS地址')
    text=text.strip();u=urllib.parse.urlsplit(text if '://' in text else 'https://'+text)
    if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('','/'):
        raise ValueError('只接受域名或IP及可选端口；不接受账号、查询参数或路径')
    try:port=u.port
    except ValueError:raise ValueError('端口不正确')
    if port is not None and not 1<=port<=65535:raise ValueError('端口超出范围')
    host=u.hostname.encode('idna').decode('ascii')
    if any(c.isspace() for c in host) or any(c in host for c in ('\\','"','\x00')):raise ValueError('目标主机不正确')
    return u.scheme+'://'+('['+host+']' if ':' in host else host)+(':'+str(port) if port else '')+'/',host

def curl_once(url,target_ip=None):
    args=[str(BIN/'WeakNetProbeCurl.exe'),'-q','--proxy','','--noproxy','*','--connect-timeout','3','--max-time','6','--head','--output','NUL','--silent','--show-error','--no-sessionid','--write-out','%{json}',url]
    if target_ip:
        u=urllib.parse.urlsplit(url);addr=ipaddress.ip_address(target_ip)
        args[-1:-1]=['--resolve',u.hostname+':'+str(u.port or (443 if u.scheme=='https' else 80))+':'+('['+str(addr)+']' if addr.version==6 else str(addr))]
    started=time.time();p=subprocess.run(args,capture_output=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
    try:raw=json.loads(p.stdout.decode('utf-8-sig'))
    except Exception:raw={}
    fields={}
    for name,end,begin in [('dns','time_namelookup',None),('tcp','time_connect','time_namelookup'),('tls','time_appconnect','time_connect'),('ttfb','time_starttransfer',None)]:
        a=raw.get(end,0);b=raw.get(begin,0) if begin else 0
        valid=isinstance(a,(int,float)) and a>0 and a>=b
        if name=='dns' and p.returncode==6:valid=False
        if name=='tls' and not url.startswith('https:'):valid=False
        if name=='tls' and (p.returncode in (35,51,58,60,77,83,90,91) or raw.get('ssl_verify_result',0)!=0):valid=False
        numeric_host=False
        try:ipaddress.ip_address(urllib.parse.urlsplit(url).hostname);numeric_host=True
        except ValueError:pass
        not_applicable=name=='dns' and (target_ip or numeric_host) or name=='tls' and not url.startswith('https:')
        if not_applicable:valid=False
        fields[name]=metric((a-b)*1000 if valid else None,'ms','valid' if valid else 'not_applicable' if not_applicable else 'unavailable','独立curl探针·新进程·直连',time.time())
    return dict(started_at=started,finished_at=time.time(),exit_code=p.returncode,http_status=raw.get('http_code'),remote_ip=raw.get('remote_ip'),phases=fields,error=(p.stderr.decode('utf-8',errors='replace')[:500] or None),certificate_verified=p.returncode==0 and url.startswith('https:'))

def summarize_ping(rows):
    good=[r for r in rows if r.get('status')=='Success' and r.get('rtt_ms') is not None]
    rtts=[r['rtt_ms'] for r in good];diffs=[abs(b['rtt_ms']-a['rtt_ms']) for a,b in zip(good,good[1:]) if b['seq']==a['seq']+1]
    n=len(rows);stamp=time.time()
    return dict(sent=n,received=len(good),unanswered=n-len(good),rtt=metric(statistics.median(rtts) if rtts else None,'ms','valid' if rtts else 'no_reply','独立ICMP探针',stamp),jitter=metric(statistics.mean(diffs) if diffs else None,'ms','valid' if diffs else 'insufficient_samples','相邻成功ICMP RTT绝对差的均值',stamp),unanswered_rate=metric((n-len(good))/n*100 if n and good else None,'%','valid' if good else 'no_reply','ICMP探针未应答率，非业务丢包率',stamp),note=None if good else '目标可能过滤ICMP，不能据此判定100%业务丢包')

class Diagnostics:
    def __init__(self,catalog,controls):
        self.catalog=catalog;self.controls=controls;self.jobs={};self.lock=threading.RLock()
        for path in sorted(LOG.glob('diagnostic-*.json'),key=lambda p:p.stat().st_mtime)[-100:]:
            try:
                job=read(path)
                if job and job.get('id') and job.get('state') in ('complete','failed'):self.jobs[job['id']]=job
            except (ValueError,OSError):pass
    def start(self,ident,text,target_ip=None):
        app=self.catalog.detail(ident);url,host=target_url(text)
        if target_ip:
            target_ip=str(ipaddress.ip_address(target_ip))
            if target_ip not in {c.get('remote_ip') for c in app['connections']}:raise ValueError('目标IP不在所选程序当前连接中')
        with self.lock:
            if any(j['state']=='running' for j in self.jobs.values()):raise ValueError('已有诊断正在运行，请等待完成')
            job=dict(id=uuid.uuid4().hex,app_id=ident,app_name=app['name'],url=url,host=host,target_ip=target_ip,state='running',started_at=now(),https=[],icmp=None,policy=dict(mode='direct',config_synced=False,protocol_coverage_confirmed=False,note='独立进程直连测量，不代表程序自身请求'))
            self.jobs[job['id']]=job;threading.Thread(target=self.run,args=(job,),daemon=True).start();return dict(job)
    def run(self,job):
        leases=[]
        try:
            active=[l for p,l in nb.active_leases() if key(l['path'])==job['app_id'] and l['state']=='active']
            if active:
                l=active[0];seconds=max(1,int(l['expires_epoch_s']-time.time()))
                if not self.controls.gate()['available']:raise RuntimeError('无法确认探针的同档位规则，未启动该次对照诊断')
                up,down=nb.lease_parameters(l)
                for exe in ('WeakNetProbeCurl.exe','WeakNetICMP.exe'):
                    leases.append(nb.begin_lease(BIN/exe,l['mode'],up,down,seconds,'内部诊断探针'))
                job['policy']=dict(mode=l['mode'],config_synced=True,protocol_coverage_confirmed=False,expires_epoch_s=l['expires_epoch_s'],note='已回读相同配置，TCP/ICMP协议实际覆盖仍须验证；跨恢复时刻的样本分开解释')
                if l['mode']=='drop':job['policy'].update(upstream_drop_pct=up,downstream_drop_pct=down,actual_drop_pct=None)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                ping=pool.submit(subprocess.run,[str(BIN/'WeakNetICMP.exe'),'--ping',job.get('target_ip') or job['host'],'20'],capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
                if job.get('target_ip'):
                    start=time.perf_counter()
                    try:socket.getaddrinfo(job['host'],443);job['dns']=metric((time.perf_counter()-start)*1000,'ms','valid','Windows DNS解析·固定IP连接前的独立采样',time.time())
                    except socket.gaierror:job['dns']=metric(None,'ms','unavailable','Windows DNS解析失败',time.time())
                for i in range(3):
                    try:sample=curl_once(job['url'],job.get('target_ip'));sample['seq']=i+1
                    except Exception as ex:sample=dict(seq=i+1,error=str(ex),phases={},exit_code=None)
                    sample['during_configured_impairment']=job['policy'].get('config_synced',False) and time.time()<job['policy'].get('expires_epoch_s',0)
                    with self.lock:job['https'].append(sample)
                result=ping.result();data=json.loads(result.stdout.decode('utf-8-sig'))
                with self.lock:job['icmp']=dict(samples=data['samples'],summary=summarize_ping(data['samples']))
            job['state']='complete'
        except Exception as ex:job.update(state='failed',error=str(ex))
        finally:
            for lease in leases:
                try:nb.restore_lease(DATA/'leases'/(lease['id']+'.json'))
                except Exception as ex:job.update(state='failed',error='探针规则恢复未确认：'+str(ex))
            job['finished_at']=now();write(LOG/('diagnostic-'+job['id']+'.json'),job)
    def get(self,ident=None):
        with self.lock:
            rows=[j for j in self.jobs.values() if ident is None or j['app_id']==ident]
            return json.loads(json.dumps(rows[-1])) if rows else None
