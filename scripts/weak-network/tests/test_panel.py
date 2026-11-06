import os as _publication_os
from pathlib import Path as _PublicationPath
import unittest,sys,time,json,tempfile,threading,subprocess,io,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import common,catalog,netbalancer as nb,diagnostics,server,recovery
from control_manager import ControlManager

def proc(pid=1,path=r'C:\Apps\one.exe',birth=10):return dict(pid=pid,path=path,birth=birth,name=Path(path).name if path else 'unknown.exe')
def sample(processes=None,status='valid',counters=None,connections=None,stamp=None,collector_id='one'):
    return dict(processes=processes or [proc()],connections=connections or [],counters=counters or [],etw=dict(status=status,code=0),sampled_at=stamp or time.time(),collector_id=collector_id,collector_pid=4,admin=status!='permission_required')
def counter(pid=1,birth=10,sent=0,received=0,path=r'C:\Apps\one.exe'):return dict(pid=pid,birth=birth,path=path,sent=sent,received=received)
def conn(pid=1,birth=10,rtt=None,status='not_selected'):return dict(pid=pid,birth=birth,protocol='TCP',tcp_state=5,estats=dict(status=status,rtt_ms=rtt,retransmitted_segments=2))

class CatalogTests(unittest.TestCase):
    def test_merge_same_full_path(self):self.assertEqual(len(catalog.grouped([proc(),proc(2)])),1)
    def test_same_name_different_paths(self):self.assertEqual(len(catalog.grouped([proc(),proc(2,r'C:\Other\one.exe')])),2)
    def test_unknown_path_not_merge(self):self.assertEqual(len(catalog.grouped([proc(1,None),proc(2,None)])),2)
    def test_pid_reuse_does_not_inherit_traffic(self):
        c=catalog.Catalog();t=time.time();c.ingest(sample(counters=[counter(sent=100)],stamp=t));c.ingest(sample([proc(birth=20)],counters=[counter(birth=20,sent=7)],stamp=t+1));a=c.detail(common.key(proc()['path']));self.assertEqual(a['metrics']['upload']['value'],7)
    def test_old_connection_pid_generation_excluded(self):
        c=catalog.Catalog();c.ingest(sample([proc(birth=20)],connections=[conn(birth=10)]));self.assertEqual(c.detail(common.key(proc()['path']))['connections'],[])
    def test_permission_not_zero(self):
        c=catalog.Catalog();c.ingest(sample(status='permission_required'));m=c.detail(common.key(proc()['path']))['metrics'];self.assertIsNone(m['upload']['value']);self.assertEqual(m['upload']['status'],'permission_required')
    def test_stale_null(self):
        c=catalog.Catalog();c.ingest(sample(stamp=time.time()-6));self.assertEqual(c.detail(common.key(proc()['path']))['metrics']['connections']['status'],'stale')
    def test_exit_clears_connections_and_values(self):
        c=catalog.Catalog();c.ingest(sample());ident=common.key(proc()['path']);c.select(ident);c.ingest(sample([proc(2,r'C:\Other\two.exe')],stamp=time.time()+1));a=c.detail(ident);self.assertTrue(a['exited']);self.assertEqual(a['pids'],[]);self.assertIsNone(a['metrics']['upload']['value'])
    def test_select_does_not_control(self):
        c=catalog.Catalog();c.ingest(sample());
        with patch.object(nb,'apply_config') as apply:c.select(common.key(proc()['path']));apply.assert_not_called()
    def test_probe_not_added_to_program_counters(self):
        c=catalog.Catalog();c.ingest(sample(counters=[counter(path=str(common.BIN/'WeakNetProbeCurl.exe'),sent=100)]));self.assertEqual(c.detail(common.key(proc()['path']))['metrics']['uploaded']['value'],0)
    def test_multiple_rtt_range_and_coverage(self):
        c=catalog.Catalog();c.ingest(sample(connections=[conn(rtt=10,status='valid'),conn(rtt=45,status='valid'),conn()]));m=c.detail(common.key(proc()['path']))['metrics']['rtt']['value'];self.assertEqual((m['min'],m['max'],m['covered'],m['eligible']),(10,45,2,3))
    def test_invalid_estats_not_used(self):
        c=catalog.Catalog();c.ingest(sample(connections=[conn(rtt=100,status='unavailable')]));self.assertIsNone(c.detail(common.key(proc()['path']))['metrics']['rtt']['value'])
    def test_existing_vendor_rule_only_monitor(self):
        c=catalog.Catalog();c.ingest(sample());a=c.list(dict(available=True,reason=None,existing_program_ids=[common.key(proc()['path'])]))[0];self.assertFalse(a['can_control']);self.assertEqual(a['capability'],'仅监控')

class AdapterTests(unittest.TestCase):
    def test_runtime_reader_does_not_use_saved_xml(self):
        result=MagicMock(returncode=0,stdout=json.dumps(dict(status='valid',records=[],source='authenticated IPC',sampled_at=time.time())).encode())
        with patch.object(nb.subprocess,'run',return_value=result) as run,patch.object(nb,'disk_records',side_effect=AssertionError('stale file read')):
            self.assertEqual(nb.records('known.exe'),[]);self.assertEqual(Path(run.call_args.args[0][0]).name,'NetBalancerReadback.exe')
    def test_reader_failure_not_absent_rule(self):
        result=MagicMock(returncode=1,stdout=b'{"status":"unavailable","error":"access denied"}')
        with patch.object(nb.subprocess,'run',return_value=result),self.assertRaisesRegex(RuntimeError,'access denied'):nb.records('known.exe')
    def test_old_gate_missing_reader_fingerprint_invalid(self):
        with patch.object(nb,'fingerprints',return_value=dict(reader_sha256='new')):self.assertFalse(nb.verified(dict(passed=True,nb_sha256='old')))
    def test_direction_mapping(self):self.assertEqual((nb.desired('delay',70,130)['up_value'],nb.desired('delay',70,130)['down_value']),(70,130))
    def test_outage_both_sides(self):self.assertEqual((nb.desired('outage')['up'],nb.desired('outage')['down']),('Blocked','Blocked'))
    def test_delay_zero_direction_normal(self):self.assertEqual(nb.desired('delay',0,100)['up'],'Normal')
    def test_cli_direction_order(self):
        with patch.object(nb,'cli',return_value='') as cli:nb.apply_config('known.exe',nb.desired('delay',70,130));args=cli.call_args.args[0];self.assertEqual(args[4:8],['Delayed','Delayed',130,70])
    def test_existing_rule_not_overwritten(self):
        with patch.object(nb,'snapshot',return_value=dict(exists=True,config=nb.desired('delay'))),patch.object(nb,'apply_config') as apply:
            with self.assertRaisesRegex(RuntimeError,'已有'):nb.begin_lease('one.exe','delay',100,100,10,require_gate=False)
            apply.assert_not_called()
    def lease(self,root):
        file=Path(root)/'one.json';original=dict(exists=False,config=nb.desired('delay',0,0));lease=dict(id='one',path='one.exe',label='one.exe',state='active',original=original,written=nb.desired('delay',100,100));common.write(file,lease);return file,lease
    def test_restore_original(self):
        with tempfile.TemporaryDirectory() as root:
            p,l=self.lease(root)
            with patch.object(nb,'snapshot',return_value=dict(config=l['written'])),patch.object(nb,'apply_config') as apply,patch.object(nb,'wait_config',return_value=l['original']),patch.object(nb,'audit'):
                self.assertTrue(nb.restore_lease(p));self.assertEqual(apply.call_args.args[1],l['original']['config']);self.assertEqual(common.read(p)['state'],'restored')
    def test_external_edit_conflict_no_write(self):
        with tempfile.TemporaryDirectory() as root:
            p,l=self.lease(root)
            with patch.object(nb,'snapshot',return_value=dict(config=nb.desired('outage'))),patch.object(nb,'apply_config') as apply:self.assertFalse(nb.restore_lease(p));apply.assert_not_called();self.assertEqual(common.read(p)['state'],'conflict')
    def test_dormant_field_external_change_also_conflict(self):
        with tempfile.TemporaryDirectory() as root:
            p,l=self.lease(root);l['actual']=dict(records=[dict(fields=dict(DownloadLimit='0'))]);common.write(p,l)
            current=dict(exists=True,config=l['written'],records=[dict(fields=dict(DownloadLimit='8192'))])
            with patch.object(nb,'snapshot',return_value=current),patch.object(nb,'apply_config') as apply:self.assertFalse(nb.restore_lease(p));apply.assert_not_called()
    def test_old_timer_no_write_after_restore(self):
        with tempfile.TemporaryDirectory() as root:
            p,l=self.lease(root);l['state']='restored';common.write(p,l)
            with patch.object(nb,'apply_config') as apply:self.assertTrue(nb.restore_lease(p));apply.assert_not_called()
    def test_recovery_expired_invokes_restore(self):
        with tempfile.TemporaryDirectory() as root:
            p,l=self.lease(root);l['expires_epoch_s']=time.time()-1;common.write(p,l)
            with patch.object(sys,'argv',['recovery.py',str(p)]),patch.object(recovery,'restore_lease',return_value=True) as restore:recovery.main();restore.assert_called_once_with(p)
    def test_startup_recovers_prior_records(self):
        with patch.object(nb,'active_leases',return_value=[(Path('owned.json'),dict(id='owned'))]),patch.object(nb,'restore_lease',return_value=True) as restore,patch('control_manager.read',return_value={}):ControlManager(None).recover_startup();restore.assert_called_once()
    def test_emergency_only_owned_records(self):
        with patch.object(nb,'active_leases',return_value=[]),patch.object(nb,'apply_config') as apply:ControlManager(None).restore();apply.assert_not_called()

class DiagnosticTests(unittest.TestCase):
    def test_reject_credentials_path_query(self):
        for text in ['https://user:pass@example.com/','https://example.com/private','ftp://example.com','https://example.com/?token=x','--config evil']:
            with self.subTest(text=text),self.assertRaises(ValueError):diagnostics.target_url(text)
    def test_valid_domain(self):self.assertEqual(diagnostics.target_url('example.com')[0],'https://example.com/')
    def curl(self,code,raw):
        result=MagicMock(returncode=code,stdout=json.dumps(raw).encode(),stderr=b'')
        with patch.object(diagnostics.subprocess,'run',return_value=result) as run:out=diagnostics.curl_once('https://example.com/');return out,run.call_args.args[0]
    def test_direct_no_proxy_new_connections(self):
        _,args=self.curl(0,{});self.assertEqual(args[1],'-q');self.assertEqual(args[args.index('--proxy')+1],'');self.assertIn('--noproxy',args);self.assertNotIn('--insecure',args)
    def test_dns_failure_not_success_zero(self):
        out,_=self.curl(6,dict(time_namelookup=0));self.assertIsNone(out['phases']['dns']['value']);self.assertFalse(out['certificate_verified'])
    def test_tls_failure_not_valid(self):
        out,_=self.curl(60,dict(time_connect=.1,time_appconnect=.2,ssl_verify_result=20));self.assertIsNone(out['phases']['tls']['value']);self.assertFalse(out['certificate_verified'])
    def test_icmp_filtered_not_business_loss(self):
        result=diagnostics.summarize_ping([dict(seq=i,status='TimedOut',rtt_ms=None) for i in range(20)]);self.assertIsNone(result['unanswered_rate']['value']);self.assertIn('不能',result['note'])
    def test_jitter_does_not_bridge_failed_samples(self):
        s=diagnostics.summarize_ping([dict(seq=1,status='Success',rtt_ms=10),dict(seq=3,status='Success',rtt_ms=20)]);self.assertIsNone(s['jitter']['value'])
    def test_target_ip_must_be_from_selected_program(self):
        c=MagicMock();c.detail.return_value=dict(connections=[])
        with self.assertRaisesRegex(ValueError,'当前连接'):diagnostics.Diagnostics(c,None).start('id','example.com','1.2.3.4')

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.c=MagicMock();self.c.detail.return_value=dict(protection_reason=None,exited=False,path=r'C:\Apps\one.exe',name='one.exe',instances=[dict(pid=1,birth=10)])
        self.manager=ControlManager(self.c);self.gate=patch.object(self.manager,'gate',return_value=dict(available=True,reason=None));self.gate.start()
    def tearDown(self):self.gate.stop()
    def test_protected_program(self):
        self.c.detail.return_value['protection_reason']='仅允许监控'
        with self.assertRaisesRegex(ValueError,'仅允许监控'):self.manager.apply('id',{})
    def test_engine_permission_failure(self):
        self.manager.gate.return_value=dict(available=False,reason='缺少权限')
        with self.assertRaisesRegex(ValueError,'缺少权限'):self.manager.apply('id',{})
    def test_invalid_duration_or_mode(self):
        for value in [dict(mode='outage',seconds=61),dict(mode='delay',seconds=301),dict(mode='delay',seconds=0),dict(mode='delay',seconds=1.5),dict(mode='drop',seconds=10),dict(mode='delay',seconds=2,upstream_ms=3001)]:
            with self.subTest(value=value),self.assertRaises(ValueError):self.manager.apply('id',value)
    def test_other_active_control_not_retargeted(self):
        with patch.object(nb,'active_leases',return_value=[('file',{})]),patch.object(nb,'begin_lease') as begin:
            with self.assertRaisesRegex(ValueError,'已有控制'):self.manager.apply('id',dict(mode='delay',seconds=10))
            begin.assert_not_called()
    def test_reused_pid_rejected_before_write(self):
        with patch.object(nb,'active_leases',return_value=[]),patch('collector_client.query',return_value=dict(processes=[proc(birth=20)])),patch.object(nb,'begin_lease') as begin:
            with self.assertRaisesRegex(ValueError,'实例已变化'):self.manager.apply('id',dict(mode='delay',seconds=10))
            begin.assert_not_called()

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=server.Panel();cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);cls.http.panel=cls.p;threading.Thread(target=cls.http.serve_forever,daemon=True).start();cls.url='http://127.0.0.1:'+str(cls.http.server_port);cls.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close()
    def request(self,path,body=None,auth=True,origin='http://127.0.0.1:18492',host='127.0.0.1:18492'):
        headers={'Host':host,'Origin':origin,'Content-Type':'application/json'}
        if auth:headers['X-Session-Token']=self.p.token
        request=urllib.request.Request(self.url+path,None if body is None else json.dumps(body).encode(),headers)
        try:
            with self.opener.open(request) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    def test_unauthenticated_rejected(self):self.assertEqual(self.request('/api/programs',auth=False)[0],403)
    def test_external_host_rejected(self):self.assertEqual(self.request('/api/programs',host='evil.example:18492')[0],403)
    def test_cross_origin_rejected(self):self.assertEqual(self.request('/api/session',{},origin='https://evil.example')[0],403)
    def test_old_unscoped_control_rejected(self):self.assertEqual(self.request('/api/control',{})[0],400)
    def test_arbitrary_app_path_not_discovered(self):self.assertEqual(self.request('/api/control',dict(app_id=r'C:\arbitrary.exe',mode='delay'))[0],400)
    def test_no_command_endpoint(self):self.assertEqual(self.request('/api/command',dict(command='whoami'))[0],400)
    def test_session_cookie_httponly(self):self.assertEqual(self.request('/api/session',{})[0],200)

if __name__=='__main__':unittest.main(verbosity=2)
