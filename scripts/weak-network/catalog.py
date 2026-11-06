import os as _publication_os
from pathlib import Path as _PublicationPath
from common import *
from collections import deque
import collector_client
import ipaddress

def control_coverage(connections):
    local=[]
    for c in connections:
        try:is_loopback=ipaddress.ip_address(c.get('remote_ip') or '').is_loopback
        except ValueError:is_loopback=False
        if c['protocol']=='TCP' and c.get('tcp_state')==5 and is_loopback:
            local.append(dict(pid=c['pid'],remote_ip=c['remote_ip'],remote_port=c['remote_port']))
    return dict(status='unverified',local_forwarding_detected=bool(local),connections=local,reason='检测到本机中转连接（可能为代理）；损伤覆盖未验证' if local else '当前仅验证配置回读，实际业务损伤覆盖未验证')

def metric(value,unit,status,source,stamp,window=None):return dict(value=value,unit=unit,status=status,source=source,sampled_at=stamp,window_s=window)
def grouped(processes):
    out={}
    for p in processes:
        path=p.get('path');ident=key(path) if path else key('unknown:'+str(p['pid'])+':'+str(p['birth']))
        if ident not in out:out[ident]=dict(id=ident,name=Path(path).name if path else p['name'],path=path,pids=[],instances=[],path_status=p.get('path_status','valid'))
        out[ident]['pids'].append(p['pid']);out[ident]['instances'].append(dict(pid=p['pid'],birth=p['birth']))
    return out

class Catalog:
    def __init__(self):
        self.lock=threading.RLock();self.apps={};self.last_counters={};self.collector_id=None;self.last_stamp=None;self.observed_since=None;self.selected=None;self.selection_sent=None;self.error=None;self.system={};self.stop=threading.Event();self.icons={}
    def protected(self,app):
        path=(app.get('path') or '').lower();name=app['name'].lower()
        if not path:return '缺少可执行文件路径权限'
        if path.startswith(str(ROOT).lower()):return '本工具或内部探针，只允许监控'
        if path==str(PYTHON).lower():return '与面板后台共用Python运行时，只允许监控'
        if '\\netbalancer\\' in path or name in ('system.exe','idle.exe','svchost.exe','lsass.exe','services.exe','wininit.exe','csrss.exe','smss.exe','winlogon.exe'):return '关键系统或网络控制进程，只允许监控'
        return None
    def ingest(self,s):
        if 'processes' not in s:raise RuntimeError('Windows采集正在初始化')
        stamp=s['sampled_at'];groups=grouped(s['processes']);conns=s.get('connections',[]);etw=s['etw'];status=etw['status']
        if self.collector_id!=s['collector_id']:
            self.last_counters={};self.last_stamp=None;self.selection_sent=None;self.collector_id=s['collector_id'];self.observed_since=s.get('started_at',stamp)
            with self.lock:
                for app in self.apps.values():app['total_up']=0;app['total_down']=0;app['history'].clear()
        delta_t=stamp-self.last_stamp if self.last_stamp else max(.001,stamp-s.get('started_at',stamp-1))
        if delta_t<=0:return
        increments={}
        for c in s.get('counters',[]):
            ident=key(c['path']);proc=(c['pid'],str(c['birth']));old=self.last_counters.get(proc,dict(sent=0,received=0));ds=max(0,c['sent']-old['sent']);dr=max(0,c['received']-old['received']);self.last_counters[proc]=c
            accum=increments.setdefault(ident,[0,0]);accum[0]+=ds;accum[1]+=dr
        with self.lock:
            for ident,g in groups.items():
                old=self.apps.get(ident,{});history=old.get('history',deque(maxlen=60));total_up=old.get('total_up',0);total_down=old.get('total_down',0);du,dd=increments.get(ident,[0,0]);total_up+=du;total_down+=dd
                generations={(p['pid'],str(p['birth'])) for p in g['instances']}
                own=[c for c in conns if (c['pid'],str(c.get('birth'))) in generations];established=any(c['protocol']=='TCP' and c['tcp_state']==5 for c in own);udp=any(c['protocol']=='UDP' for c in own)
                active=stamp if du or dd or (status not in ('valid','partial') and (established or udp)) else old.get('last_activity',0)
                rates_valid=status in ('valid','partial');up=du/delta_t if rates_valid else None;down=dd/delta_t if rates_valid else None
                history.append(dict(at=stamp,up_bps=up,down_bps=down,status=status))
                rtt=[c['estats']['rtt_ms'] for c in own if c.get('estats',{}).get('status')=='valid' and c['estats'].get('rtt_ms') is not None]
                retrans=[c['estats']['retransmitted_segments'] for c in own if c.get('estats',{}).get('status') in ('valid','waiting') and 'retransmitted_segments' in c['estats']]
                eligible=[c for c in own if c['protocol']=='TCP' and c['tcp_state']==5]
                missing_tcp='not_applicable' if not eligible else 'permission_required' if not s['admin'] else 'waiting' if any(c.get('estats',{}).get('status')=='waiting' for c in eligible) else 'unavailable'
                reason=self.protected(g)
                g.update(connections=own,total_up=total_up,total_down=total_down,last_activity=active,history=history,icon=self.icons.get(ident),exited=False,protection_reason=reason,
                    metrics=dict(upload=metric(up,'B/s',status,'Windows ETW',stamp,delta_t),download=metric(down,'B/s',status,'Windows ETW',stamp,delta_t),uploaded=metric(total_up if rates_valid else None,'B',status,'Windows ETW·本次观察累计',stamp),downloaded=metric(total_down if rates_valid else None,'B',status,'Windows ETW·本次观察累计',stamp),connections=metric(len(own),'个','valid','Windows IP Helper·TCP连接及UDP本地端点',stamp),rtt=metric(dict(min=min(rtt),max=max(rtt),covered=len(rtt),eligible=sum(c['protocol']=='TCP' and c['tcp_state']==5 for c in own)) if rtt else None,'ms','valid' if rtt else 'permission_required' if not s['admin'] else 'unavailable','所选程序TCP连接·Windows EStats',stamp),retransmissions=metric(sum(retrans) if retrans else None,'段','valid' if retrans else 'permission_required' if not s['admin'] else 'unavailable','所选程序TCP连接·Windows EStats',stamp)))
                for name in ('uploaded','downloaded'):g['metrics'][name]['window_s']=max(0,stamp-self.observed_since)
                for name in ('rtt','retransmissions'):
                    if g['metrics'][name]['value'] is None:g['metrics'][name]['status']=missing_tcp
                g['metrics']['rtt']['coverage']=dict(covered=len(rtt),eligible=len(eligible))
                self.apps[ident]=g
            for ident,a in list(self.apps.items()):
                if ident not in groups:
                    a['exited']=True;a['pids']=[];a['instances']=[];a['connections']=[]
                    for m in a['metrics'].values():m['status']='stale';m['value']=None
                    if stamp-a.get('last_activity',0)>60 and ident!=self.selected:del self.apps[ident]
            self.system=dict(admin=s['admin'],etw=etw,collector_pid=s['collector_pid'],sampled_at=stamp,observation_started_at=self.observed_since);self.last_stamp=stamp;self.error=None
    def run(self):
        while not self.stop.is_set():
            try:
                s=collector_client.query(dict(op='snapshot'));self.ingest(s)
                with self.lock:app=self.apps.get(self.selected);pids=tuple(sorted(app['pids'])) if app else ()
                if pids!=self.selection_sent:collector_client.query(dict(op='select',pids=pids));self.selection_sent=pids
            except Exception as ex:self.error=str(ex)
            self.stop.wait(1)
    def select(self,ident):
        with self.lock:
            if ident not in self.apps:raise ValueError('程序已退出或不存在')
            self.selected=ident
    def list(self,gate):
        with self.lock:
            now_s=time.time();rows=[]
            for a in self.apps.values():
                reason=a['protection_reason'] or ('已有优先级规则，尚未验证其无损恢复，仅供监控' if a['id'] in gate.get('existing_program_ids',[]) else None);can=gate['available'] and not reason and not a['exited']
                cap='可控制' if can else '缺少权限' if not a.get('path') else '仅监控' if reason else '控制引擎不可用'
                stale=self.error is not None or now_s-self.system.get('sampled_at',0)>4
                rows.append({k:a[k] for k in ('id','name','path','pids','instances','icon','exited')}|dict(upload=None if stale else a['metrics']['upload'],download=None if stale else a['metrics']['download'],network_active=now_s-a['last_activity']<60,capability=cap,can_control=can,reason=reason or (None if can else gate['reason'])))
            return sorted(rows,key=lambda a:(not a['network_active'],a['name'].lower(),a['path'] or ''))
    def detail(self,ident):
        with self.lock:
            if ident not in self.apps:raise ValueError('程序已退出或不存在')
            a=self.apps[ident];out=dict(a,history=list(a['history']),system=self.system,error=self.error,control_coverage=control_coverage(a['connections']))
            if self.error or time.time()-self.system.get('sampled_at',0)>4:
                out['metrics']={k:dict(m,value=None,status='stale') for k,m in a['metrics'].items()}
            return out
    def icon(self,ident):
        with self.lock:
            a=self.apps.get(ident)
            if not a or not a['path']:return None
            if ident in self.icons:return self.icons[ident]
            path=a['path']
        try:icon=collector_client.query(dict(op='icon',path=path)).get('png')
        except Exception:icon=None
        with self.lock:self.icons[ident]=icon
        return icon
