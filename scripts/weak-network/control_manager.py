import os as _publication_os
from pathlib import Path as _PublicationPath
from common import *
import netbalancer as nb
class ControlManager:
    def __init__(self,catalog):self.catalog=catalog;self.lock=threading.RLock();self.recovery_errors=[];self.priority_cache=(0,[])
    def gate(self):
        if not NB.exists():return dict(available=False,reason='未安装NetBalancer')
        service=nb.service_status()
        if not service['available']:return dict(available=False,reason=service['reason'],service=service)
        gate=read(DATA/'engine-verification.json',{})
        if not gate.get('passed'):return dict(available=False,reason=gate.get('reason','尚未通过隔离控制自检，请运行“离线自检”'),verification=gate)
        if not nb.verified(gate):return dict(available=False,reason='控制组件已变化，需要重新进行隔离自检',verification=gate)
        if self.recovery_errors:return dict(available=False,reason='存在未恢复的程序配置，请先核对恢复',verification=gate)
        try:
            if time.monotonic()-self.priority_cache[0]>1:self.priority_cache=(time.monotonic(),[key(r['Key']) for r in nb.live_priorities()['records']])
        except Exception as ex:return dict(available=False,reason='实时配置读取失败：'+str(ex),verification=gate)
        owned=[key(l['path']) for p,l in nb.active_leases()]
        modes={mode:dict(available=nb.mode_verified(gate,mode),reason=None if nb.mode_verified(gate,mode) else gate.get('modes',{}).get(mode,{}).get('reason','该模式尚未完成隔离自检')) for mode in ('delay','outage','drop')}
        return dict(available=True,reason=None,verification=gate,modes=modes,existing_program_ids=[i for i in self.priority_cache[1] if i not in owned])
    def recover_startup(self):
        guard=read(DATA/'selftest-guard.json',{})
        if guard.get('state')=='armed':
            try:
                nb.apply_config(BIN/'WeakNetProbeCurl.exe',guard['original']['config']);guard['state']='recovered';write(DATA/'selftest-guard.json',guard)
            except Exception:self.recovery_errors.append('隔离自检探针')
        for p,lease in nb.active_leases():
            try:
                if not nb.restore_lease(p):self.recovery_errors.append(lease['id'])
            except Exception:self.recovery_errors.append(lease['id'])
    def status(self):
        rows=[]
        for p,l in nb.active_leases():
            row=dict(id=l['id'],app_id=key(l['path']),label=l['label'],mode=l['mode'],remaining_s=max(0,l['expires_epoch_s']-time.time()),state=l['state'],error=l.get('error'),coverage_status='unverified')
            up,down=nb.lease_parameters(l)
            if l['mode']=='drop':
                row.update(upstream_drop_pct=up,downstream_drop_pct=down,actual_drop_pct=dict(upstream=None,downstream=None,unit='%',status='unavailable',source='未接入包级丢弃计数',sampled_at=None,reason='配置概率不等于实测业务丢包率'))
            elif l['mode']=='delay':row.update(upstream_ms=up,downstream_ms=down)
            rows.append(row)
        return dict(active=rows,gate=self.gate())
    def apply(self,ident,data):
        with self.lock:
            app=self.catalog.detail(ident)
            if app['protection_reason']:raise ValueError(app['protection_reason'])
            if app['exited']:raise ValueError('程序已经退出')
            gate=self.gate()
            if not gate['available']:raise ValueError(gate['reason'])
            mode=data.get('mode')
            if mode not in ('delay','outage','drop'):raise ValueError('请选择附加延迟、概率丢包或连接中断')
            capability=gate.get('modes',{}).get(mode)
            if capability and not capability['available']:raise ValueError(capability['reason'])
            def integer(value,name,maximum):
                if type(value) is not int or value<0 or value>maximum:raise ValueError(name+'超出允许的整数范围')
                return value
            seconds=integer(data.get('seconds'),'持续时间',60 if mode=='outage' else 300)
            if seconds<1:raise ValueError('持续时间至少1秒')
            if mode=='drop':
                if data.get('upstream_ms',0)!=0 or data.get('downstream_ms',0)!=0:raise ValueError('概率丢包不能叠加非零延迟')
                up=integer(data.get('upstream_drop_pct'),'上行丢包概率',100);down=integer(data.get('downstream_drop_pct'),'下行丢包概率',100)
            else:
                if data.get('upstream_drop_pct',0)!=0 or data.get('downstream_drop_pct',0)!=0:raise ValueError('当前模式不能叠加丢包概率')
                up=integer(data.get('upstream_ms',0),'上行延迟',3000);down=integer(data.get('downstream_ms',0),'下行延迟',3000)
            active=nb.active_leases()
            if active:raise ValueError('已有控制任务，请先恢复其原设置')
            # Revalidate live process identity immediately before writing.
            snapshot=__import__('collector_client').query(dict(op='snapshot'))
            valid={(p['pid'],str(p['birth'])) for p in snapshot['processes'] if p.get('path') and os.path.normcase(p['path'])==os.path.normcase(app['path'])}
            if not any((p['pid'],str(p['birth'])) in valid for p in app['instances']):raise ValueError('程序实例已变化，请重新选择')
            if mode in ('delay','drop') and up==down==0:return dict(restored=True,reason='双向参数为零，无需修改原设置')
            return nb.begin_lease(app['path'],mode,up,down,seconds,app['name'])
    def restore(self,ident=None):
        failures=[]
        if ident and not any(key(l['path'])==ident for _,l in nb.active_leases()):raise ValueError('该程序没有本工具持有的控制记录')
        for p,l in nb.active_leases():
            if ident and key(l['path'])!=ident:continue
            try:
                if not nb.restore_lease(p):failures.append(l['label'])
            except Exception:failures.append(l['label'])
        self.recovery_errors=failures
        if failures:raise ValueError('恢复尚未确认：'+', '.join(failures))
        return dict(restored=True)
