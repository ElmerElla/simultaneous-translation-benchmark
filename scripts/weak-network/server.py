import os as _publication_os
from pathlib import Path as _PublicationPath
"""Loopback-only authenticated API. No arbitrary executable/command endpoints."""
from common import *
import atexit, csv, hmac, http.cookies, io, secrets, subprocess, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import collector_client
from catalog import Catalog
from control_manager import ControlManager
from diagnostics import Diagnostics, target_url

class Panel:
    def __init__(self):
        self.token=secrets.token_urlsafe(32);self.catalog=Catalog();self.controls=ControlManager(self.catalog);self.diagnostics=Diagnostics(self.catalog,self.controls);self.selftest_lock=threading.Lock();self.selftest_running=False
    def start(self):
        self.controls.recover_startup()
        collector_client.start_normal()
        threading.Thread(target=self.catalog.run,daemon=True).start()
        write(DATA/'session.json',dict(token=self.token,pid=os.getpid(),port=PORT,app_id=APP_ID))
        subprocess.run([str(BIN/'NativeCollector.exe'),'--secure-session'],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    def engine_test(self,text):
        url,_=target_url(text)
        if not self.selftest_lock.acquire(False):raise ValueError('隔离自检正在运行')
        if self.controls.status()['active']:
            self.selftest_lock.release();raise ValueError('请先恢复当前程序设置')
        self.selftest_running=True
        def run():
            try:
                from selftest import verify
                verify(url)
            except Exception as ex:
                write(DATA/'engine-verification.json',dict(passed=False,reason=str(ex),finished_at=now()))
            finally:self.selftest_running=False;self.selftest_lock.release()
        threading.Thread(target=run,daemon=True).start()
        return dict(started=True)
    def actions(self):
        p=LOG/'actions.jsonl'
        return [json.loads(l) for l in p.read_text('utf-8').splitlines()[-300:]] if p.exists() else []
    def export(self):
        gate=self.controls.gate();apps=self.catalog.list(gate)
        return dict(format='weak-network-panel-v2',exported_at=now(),programs=[self.catalog.detail(a['id']) for a in apps],control=self.controls.status(),diagnostics=list(self.diagnostics.jobs.values()),actions=self.actions(),selftest=read(DATA/'engine-verification.json'),notes=['程序统计与独立诊断分别计量','ETW观察累计从本次采集开始；TCP重传段数不是业务丢包率','未验证的值为null并附状态；无P95'])
    def close(self):
        self.catalog.stop.set()
        try:self.controls.restore()
        except Exception as ex:audit('退出时恢复未确认',error=str(ex))
        try:collector_client.query(dict(op='stop'))
        except Exception:pass

class Handler(BaseHTTPRequestHandler):
    server_version='WeakNetPanel/2'
    def log_message(self,*args):pass # Never log session credentials or request bodies.
    @property
    def panel(self):return self.server.panel
    def reply(self,status,body,kind='application/json; charset=utf-8',headers=None):
        data=(json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8') if kind.startswith('application/json') else body.encode('utf-8') if isinstance(body,str) else body)
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for k,v in (headers or {}).items():self.send_header(k,v)
        try:self.end_headers();self.wfile.write(data)
        except (BrokenPipeError,ConnectionAbortedError,ConnectionResetError):self.close_connection=True
    def validated(self,write_request=False):
        allowed={f'127.0.0.1:{PORT}',f'localhost:{PORT}'}
        host=self.headers.get('Host','')
        if host not in allowed:raise PermissionError('不接受此访问地址')
        origin=self.headers.get('Origin')
        if origin and origin!='http://'+host:raise PermissionError('不接受跨站访问')
        if write_request and origin!='http://'+host:raise PermissionError('写操作必须来自本机面板')
        if not urllib.parse.urlsplit(self.path).path.startswith('/api/'):return
        if self.path=='/api/health':return
        supplied=self.headers.get('X-Session-Token','')
        if not write_request:
            cookie=http.cookies.SimpleCookie()
            try:cookie.load(self.headers.get('Cookie',''));supplied=supplied or (cookie['weaknet_session'].value if 'weaknet_session' in cookie else '')
            except http.cookies.CookieError:pass
        if not hmac.compare_digest(supplied,self.panel.token):raise PermissionError('启动会话无效，请从本机启动入口重新打开面板')
    def do_GET(self):
        try:
            self.validated();url=urllib.parse.urlsplit(self.path);path=url.path;params=urllib.parse.parse_qs(url.query);ident=params.get('app_id',[None])[0]
            if path=='/api/health':return self.reply(200,dict(app_id=APP_ID,pid=os.getpid()))
            if path=='/api/programs':return self.reply(200,dict(programs=self.panel.catalog.list(self.panel.controls.gate()),system=self.panel.catalog.system,error=self.panel.catalog.error,control=self.panel.controls.status(),selftest_running=self.panel.selftest_running))
            if path=='/api/program':return self.reply(200,self.panel.catalog.detail(ident))
            if path=='/api/icon':
                import base64
                icon=self.panel.catalog.icon(ident)
                return self.reply(200,base64.b64decode(icon) if icon else (ROOT/'app-icon.svg').read_bytes(),'image/png' if icon else 'image/svg+xml')
            if path=='/api/diagnostic':return self.reply(200,self.panel.diagnostics.get(ident))
            if path=='/api/actions':return self.reply(200,self.panel.actions())
            if path=='/api/selftest':return self.reply(200,dict(running=self.panel.selftest_running,result=read(DATA/'engine-verification.json')))
            if path=='/api/export':
                data=self.panel.export();fmt=params.get('format',['json'])[0]
                if fmt=='csv':
                    out=io.StringIO();w=csv.writer(out);w.writerow(['程序','路径','PID','指标','数值','单位','状态','来源','采样时间'])
                    def csv_cell(value):
                        text=str(value if value is not None else '')
                        return "'"+text if text.lstrip().startswith(('=','+','-','@')) or text.startswith(('\t','\r','\n')) else text
                    for a in data['programs']:
                        for name,m in a['metrics'].items():w.writerow([csv_cell(v) for v in [a['name'],a['path'],','.join(map(str,a['pids'])),name,json.dumps(m['value'],ensure_ascii=False),m['unit'],m['status'],m['source'],m['sampled_at']]])
                    for event in data['actions']:
                        if event.get('mode')=='drop':
                            for field,label in [('upstream_drop_pct','配置上行丢包概率'),('downstream_drop_pct','配置下行丢包概率')]:
                                w.writerow([csv_cell(v) for v in [event.get('app'),'','',label,event.get(field),'%','configured','NetBalancer配置操作记录·非实测丢弃比例',event['at']]])
                    for task in data['control']['active']:
                        if task['mode']=='drop':
                            for label in ('实测上行丢弃比例','实测下行丢弃比例'):
                                w.writerow([csv_cell(v) for v in [task['label'],'','',label,'','%','unavailable','没有可靠包级丢弃计数','']])
                    return self.reply(200,'\ufeff'+out.getvalue(),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="weaknet-v2.csv"'})
                return self.reply(200,data,headers={'Content-Disposition':'attachment; filename="weaknet-v2.json"'})
            files={'/':'index.html','/panel.js':'panel.js','/panel.css':'panel.css','/app-icon.svg':'app-icon.svg'}
            if path in files:
                kind={'html':'text/html; charset=utf-8','js':'application/javascript; charset=utf-8','css':'text/css; charset=utf-8','svg':'image/svg+xml'}[files[path].split('.')[-1]]
                return self.reply(200,(ROOT/files[path]).read_bytes(),kind)
            return self.reply(404,dict(error='接口不存在'))
        except PermissionError as ex:self.reply(403,dict(error=str(ex)))
        except (ValueError,KeyError) as ex:self.reply(400,dict(error=str(ex)))
        except Exception:self.reply(503,dict(error='本机数据暂不可用，请查看采集状态'))
    def do_POST(self):
        try:
            self.validated(True)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('只接受JSON操作')
            length=int(self.headers.get('Content-Length','0'))
            if length<0 or length>8192:raise ValueError('请求过大')
            data=json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(data,dict):raise ValueError('请求格式错误')
            path=urllib.parse.urlsplit(self.path).path;ident=data.get('app_id')
            if path=='/api/session':return self.reply(200,dict(authenticated=True),headers={'Set-Cookie':'weaknet_session='+self.panel.token+'; HttpOnly; SameSite=Strict; Path=/'})
            if path in ('/api/control','/api/restore','/api/select','/api/diagnose') and not isinstance(ident,str):raise ValueError('必须明确指定程序ID，旧版无目标控制已拒绝')
            if path=='/api/select':self.panel.catalog.select(ident);result=dict(selected=ident)
            elif path=='/api/control':
                if self.panel.selftest_running:raise ValueError('隔离自检期间不接受真实程序控制')
                result=self.panel.controls.apply(ident,data)
            elif path=='/api/restore':result=self.panel.controls.restore(ident)
            elif path=='/api/emergency-restore':result=self.panel.controls.restore()
            elif path=='/api/diagnose':
                if self.panel.selftest_running:raise ValueError('隔离自检期间请等待诊断完成')
                result=self.panel.diagnostics.start(ident,data.get('target'),data.get('target_ip'))
            elif path=='/api/selftest':result=self.panel.engine_test(data.get('target'))
            elif path=='/api/shutdown':
                self.reply(200,dict(stopping=True));threading.Thread(target=self.server.shutdown,daemon=True).start();return
            else:raise ValueError('不支持此操作')
            return self.reply(200,result)
        except PermissionError as ex:self.reply(403,dict(error=str(ex)))
        except (ValueError,KeyError,json.JSONDecodeError) as ex:self.reply(400,dict(error=str(ex)))
        except Exception as ex:self.reply(409,dict(error=str(ex)))

def main():
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler);server.daemon_threads=True;server.panel=Panel()
    try:
        server.panel.start();server.serve_forever(poll_interval=.3)
    finally:server.panel.close();server.server_close()
if __name__=='__main__':main()
