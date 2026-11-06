import os as _publication_os
from pathlib import Path as _PublicationPath
import sys,unittest,tempfile,time,json,subprocess,threading,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import common,netbalancer as nb,catalog,diagnostics,server
import selftest
from control_manager import ControlManager
import test_panel as fixtures
from test_panel import proc

def drop_lease():
    return dict(id='loss-test',path=r'C:\Apps\one.exe',label='one.exe',mode='drop',state='active',expires_epoch_s=time.time()+30,written=nb.desired('drop',10,20))

class DropAdapterTests(unittest.TestCase):
    def test_ten_percent_is_fraction(self):
        c=nb.desired('drop',10,10);self.assertEqual((c['up'],c['down'],c['up_value'],c['down_value']),('Dropped','Dropped',.1,.1));self.assertEqual(c['up_jitter'],0)
    def test_cli_download_upload_order(self):
        with patch.object(nb,'cli') as cli:nb.apply_config('known.exe',nb.desired('drop',10,20));self.assertEqual(cli.call_args.args[0][4:8],['Dropped','Dropped',.2,.1])
    def test_zero_direction_normal(self):
        self.assertEqual(nb.desired('drop',0,10)['up'],'Normal');self.assertEqual(nb.desired('drop',10,0)['down'],'Normal')
    def test_both_zero_normal(self):self.assertEqual(nb.desired('drop',0,0)['up'], 'Normal')
    def test_hundred_uses_dropped_not_blocked(self):
        c=nb.desired('drop',100,100);self.assertEqual((c['up'],c['up_value']),('Dropped',1.0))
    def test_invalid_percent(self):
        for value in [-1,101,10.5,True,'10',None,float('nan')]:
            with self.subTest(value=value),self.assertRaises(ValueError):nb.desired('drop',value,10)
    def test_mode_metadata_does_not_truncate(self):self.assertEqual(nb.lease_parameters(drop_lease()),(10,20))
    def test_old_lease_metadata_still_milliseconds(self):
        l=drop_lease();l.update(mode='delay',written=nb.desired('delay',123,456));self.assertEqual(nb.lease_parameters(l),(123,456))
    def test_legacy_gate_never_enables_drop(self):
        self.assertTrue(nb.mode_verified(dict(passed=True),'delay'));self.assertFalse(nb.mode_verified(dict(passed=True),'drop'))
    def test_drop_failure_independent_of_old_modes(self):
        g=dict(passed=True,modes=dict(delay=dict(passed=True),outage=dict(passed=True),drop=dict(passed=False)))
        self.assertTrue(nb.mode_verified(g,'delay'));self.assertTrue(nb.mode_verified(g,'outage'));self.assertFalse(nb.mode_verified(g,'drop'))
    def test_status_uses_percent_and_null_observation(self):
        m=ControlManager(None)
        with patch.object(nb,'active_leases',return_value=[(Path('owned.json'),drop_lease())]),patch.object(m,'gate',return_value={}):
            row=m.status()['active'][0];self.assertEqual(row['upstream_drop_pct'],10);self.assertEqual(row['downstream_drop_pct'],20);self.assertNotIn('upstream_ms',row);self.assertIsNone(row['actual_drop_pct']['upstream'])
    def test_dropped_snapshot_uses_drop_field(self):
        f=dict(DownloadPriority='Dropped',UploadPriority='Dropped',DownloadDelayJitter='0',UploadDelayJitter='0',PerConnectionLimits='False',DownloadDelay='0',UploadDelay='0',DownloadDropRate='0.2',UploadDropRate='0.1')
        with patch.object(nb,'records',return_value=[dict(fields=f)]):self.assertEqual(nb.snapshot('known.exe')['config']['up_value'],.1)
    def test_audit_has_percent_not_ms(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);original=dict(exists=False,config=nb.desired('delay',0,0));actual=dict(exists=True,config=nb.desired('drop',10,20),records=[])
            def spawn(args,**kwargs):Path(args[-1]).with_suffix('.ready').write_text('ready',encoding='utf-8');return MagicMock(pid=123)
            with patch.object(nb,'DATA',folder),patch.object(nb,'LOG',folder),patch.object(nb,'snapshot',return_value=original),patch.object(nb,'apply_config'),patch.object(nb,'wait_config',return_value=actual),patch.object(nb.subprocess,'Popen',side_effect=spawn),patch.object(nb,'audit') as audit:
                nb.begin_lease('known.exe','drop',10,20,10,require_gate=False);fields=audit.call_args.kwargs;self.assertEqual(fields['upstream_drop_pct'],10);self.assertNotIn('up_ms',fields)

class DropManagerTests(unittest.TestCase):
    def setUp(self):
        self.c=MagicMock();self.c.detail.return_value=dict(protection_reason=None,exited=False,path=proc()['path'],name='one.exe',instances=[dict(pid=1,birth=10)])
        self.m=ControlManager(self.c);self.gate=dict(available=True,reason=None,modes={k:dict(available=True,reason=None) for k in ('delay','outage','drop')})
        self.patches=[patch.object(self.m,'gate',return_value=self.gate),patch.object(nb,'active_leases',return_value=[]),patch('collector_client.query',return_value=dict(processes=[proc()])),patch.object(nb,'begin_lease',return_value=dict(configured=True))]
        self.mocks=[p.start() for p in self.patches]
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
    def request(self,**values):return dict(mode='drop',seconds=10,upstream_drop_pct=10,downstream_drop_pct=10,**values)
    def test_valid_drop_payload(self):
        self.m.apply('known',dict(mode='drop',seconds=300,upstream_drop_pct=10,downstream_drop_pct=20));self.assertEqual(self.mocks[-1].call_args.args[1:5],('drop',10,20,300))
    def test_invalid_api_percent(self):
        for v in [-1,101,10.5,True,'10',None]:
            with self.subTest(value=v),self.assertRaises(ValueError):self.m.apply('known',dict(mode='drop',seconds=10,upstream_drop_pct=v,downstream_drop_pct=10))
        self.mocks[-1].assert_not_called()
    def test_delay_and_drop_cannot_mix(self):
        with self.assertRaisesRegex(ValueError,'叠加'):self.m.apply('known',self.request(upstream_ms=1))
        with self.assertRaisesRegex(ValueError,'叠加'):self.m.apply('known',dict(mode='delay',seconds=10,upstream_drop_pct=10))
    def test_zero_drop_does_not_write(self):
        self.assertTrue(self.m.apply('known',dict(mode='drop',seconds=10,upstream_drop_pct=0,downstream_drop_pct=0))['restored']);self.mocks[-1].assert_not_called()
    def test_drop_unavailable_does_not_disable_delay(self):
        self.gate['modes']['drop']=dict(available=False,reason='丢包未验收')
        with self.assertRaisesRegex(ValueError,'丢包未验收'):self.m.apply('known',self.request())
        self.assertTrue(self.m.apply('known',dict(mode='delay',seconds=10,upstream_ms=100))['configured'])
    def test_loss_duration_limits(self):
        for n in (0,301,1.5):
            data=self.request();data['seconds']=n
            with self.subTest(seconds=n),self.assertRaises(ValueError):self.m.apply('known',data)

class DropCoverageTests(unittest.TestCase):
    def test_local_forwarder_warns(self):
        c=dict(protocol='TCP',tcp_state=5,pid=1,remote_ip='127.0.0.1',remote_port=7890)
        result=catalog.control_coverage([c]);self.assertTrue(result['local_forwarding_detected']);self.assertEqual(result['status'],'unverified')
    def test_direct_not_falsely_verified(self):self.assertEqual(catalog.control_coverage([])['status'],'unverified')
    def test_diagnostics_preserve_fraction_in_sync(self):
        l=drop_lease();c=MagicMock();m=MagicMock();m.gate.return_value=dict(available=True);d=diagnostics.Diagnostics(c,m)
        job=dict(id='diagnostic-test',app_id=common.key(l['path']),host='127.0.0.1',url='http://127.0.0.1/',https=[],policy={})
        leases=[dict(id='probe-curl'),dict(id='probe-icmp')]
        with patch.object(nb,'active_leases',return_value=[(None,l)]),patch.object(nb,'begin_lease',side_effect=leases) as begin,patch.object(nb,'restore_lease',return_value=True),patch.object(diagnostics,'curl_once',return_value={}),patch.object(diagnostics.subprocess,'run',return_value=MagicMock(stdout=b'{"samples":[]}')),patch.object(diagnostics,'write'):
            d.run(job);self.assertEqual(job['state'],'complete');self.assertTrue(all(call.args[2:4]==(10,20) for call in begin.call_args_list));self.assertFalse(job['policy']['protocol_coverage_confirmed']);self.assertEqual(job['policy']['upstream_drop_pct'],10)

class DropSelftestTests(unittest.TestCase):
    def test_failed_drop_check_preserves_passed_delay_and_outage(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);original=dict(exists=False,config=nb.desired('delay',0,0))
            def spawn(args,**kwargs):
                (folder/('selftest-'+args[-1]+'.ready')).write_text('ready',encoding='utf-8');return MagicMock()
            def observed(path,expected):return dict(exists=expected!=original['config'],config=expected,records=[])
            def response(ms):return dict(exit_code=0,phases=dict(tcp=dict(status='valid',value=ms)))
            with patch.object(selftest,'DATA',folder),patch.object(selftest,'LOG',folder),patch.object(selftest.subprocess,'Popen',side_effect=spawn),patch.object(selftest,'check_drop',side_effect=RuntimeError('drop rejected')),patch.object(selftest,'curl_once',side_effect=[response(10),response(10),response(220),response(220),dict(exit_code=28)]),patch.object(nb,'fingerprints',return_value={}),patch.object(nb,'active_leases',return_value=[]),patch.object(nb,'snapshot',return_value=original),patch.object(nb,'apply_config'),patch.object(nb,'wait_config',side_effect=observed):
                result=selftest._verify('https://example.com/')
            self.assertTrue(result['passed']);self.assertTrue(result['modes']['delay']['passed']);self.assertTrue(result['modes']['outage']['passed']);self.assertFalse(result['modes']['drop']['passed']);self.assertIn('drop rejected',result['modes']['drop']['reason'])

class DropHttpTests(unittest.TestCase):
    request=fixtures.HttpTests.request
    @classmethod
    def setUpClass(cls):
        cls.p=server.Panel();cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);cls.http.panel=cls.p;threading.Thread(target=cls.http.serve_forever,daemon=True).start();cls.url='http://127.0.0.1:'+str(cls.http.server_port);cls.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close()
    def test_drop_api_payload(self):
        payload=dict(app_id='known',mode='drop',seconds=10,upstream_drop_pct=10,downstream_drop_pct=20)
        with patch.object(self.p.controls,'apply',return_value=dict(configured=True)) as apply:
            self.assertEqual(self.request('/api/control',payload)[0],200);self.assertEqual(apply.call_args.args,('known',payload))
    def test_drop_api_requires_session(self):self.assertEqual(self.request('/api/control',dict(app_id='known',mode='drop'),auth=False)[0],403)
    def test_csv_exports_config_probability_percent(self):
        data=dict(programs=[],actions=[dict(mode='drop',app='one.exe',upstream_drop_pct=10,downstream_drop_pct=20,at='now')],control=dict(active=[]))
        with patch.object(self.p,'export',return_value=data):
            req=urllib.request.Request(self.url+'/api/export?format=csv',headers={'Host':'127.0.0.1:18492','X-Session-Token':self.p.token})
            with self.opener.open(req) as response:csv=response.read().decode('utf-8-sig')
        self.assertIn('配置上行丢包概率,10,%,configured',csv);self.assertNotIn('10,ms',csv)

if __name__=='__main__':unittest.main(verbosity=2)
