import json, pathlib, tempfile, time, unittest, hashlib, threading, os

ROOT=pathlib.Path(__file__).resolve().parent.parent
NS={'__name__':'test_fast_module'}
exec(compile((ROOT/os.environ.get('CODEXVIEW_TEST_SOURCE','codexview')).read_text(),'fast','exec'),NS)
SID='12345678-1234-1234-1234-123456789abc'
def record(role,text):
    return (json.dumps({'type':'response_item','payload':{'type':'message','role':role,'content':[{'text':text}]}},ensure_ascii=False)+'\n').encode()

class FastTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=pathlib.Path(self.tmp.name).resolve()
        self.path=self.home/'sessions/2026/10/20'/('rollout-2026-10-20T00-00-00-'+SID+'.jsonl');self.path.parent.mkdir(parents=True)
        self.path.write_bytes(record('user','你好')+record('assistant','Answer needle'))
        self.rt=NS['runtime'](self.home);NS['ensure_rt'](self.rt)
        self.store=NS['Store'](self.home,self.rt,[],native=False)
    def tearDown(self):self.tmp.cleanup()
    def ready(self):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            d=self.store.status(SID)
            if d['state']=='ready':return d
            if d['state']=='error':self.fail(d)
            time.sleep(.01)
        self.fail('Index timeout')
    def test_shell_discovery_and_readonly(self):
        before=self.path.read_bytes();st=self.path.stat()
        self.assertIn(SID,self.store.meta)
        self.store.model(SID);self.assertEqual(self.store.metrics['manifest_bytes'],0)
        d=self.ready();self.assertEqual(len(d['tasks']),1)
        tid=d['tasks'][0]['id'];self.assertEqual(len(self.store.task(SID,tid)['sections']),2)
        self.assertEqual(self.store.section(SID,tid,1)['text'],'Answer needle')
        self.assertEqual(self.path.read_bytes(),before);self.assertEqual(self.path.stat().st_mtime_ns,st.st_mtime_ns)
        self.assertEqual(self.store.metrics['builds'],1)
    def test_append_partial_baseline_and_restart(self):
        d=self.ready();tid=d['tasks'][0]['id'];self.store.patch(SID,tid,{'note':'keep','important':True})
        before=self.store.metrics['manifest_bytes'];tail=record('user','second')+record('assistant','next')
        with self.path.open('ab') as f:f.write(tail[:-8])
        d=self.ready();offset=self.store.manifests[SID]['offset'];self.assertLess(offset,self.path.stat().st_size)
        with self.path.open('ab') as f:f.write(tail[-8:])
        d=self.ready();self.assertEqual(len(d['tasks']),2);self.assertTrue(d['tasks'][1]['new'])
        self.assertEqual(d['review_state']['tasks'][tid]['note'],'keep')
        self.assertLessEqual(self.store.metrics['manifest_bytes']-before,len(tail))
        store=NS['Store'](self.home,self.rt,[]);idx,job=store.manifest(SID)
        self.assertEqual(job['state'],'ready');self.assertEqual(store.metrics['manifest_bytes'],0)
        self.assertNotIn('sections',idx['tasks'][0])
    def test_search_pairing_and_paging(self):
        call={'type':'response_item','payload':{'type':'function_call','name':'exec_command','call_id':'a','arguments':'needle'}}
        output={'type':'response_item','payload':{'type':'function_call_output','call_id':'a','output':'x'*300000+'needle'}}
        with self.path.open('ab') as f:f.write((json.dumps(call)+'\n'+json.dumps(output)+'\n').encode())
        d=self.ready();tid=d['tasks'][0]['id'];t=self.store.task(SID,tid)
        self.assertEqual(len(t['sections']),3);self.assertEqual(len(t['sections'][2]['parts']),2)
        page=self.store.section(SID,tid,2);self.assertEqual(len(page['text']),262144);self.assertIsNotNone(page['next_offset'])
        result=self.store.search(SID,'needle',limit=2);self.assertEqual(result['total'],2);self.assertTrue(result['truncated'])
        cancelled=threading.Event();cancelled.set();self.assertTrue(self.store.search(SID,'needle',cancel=cancelled)['cancelled'])
    def test_rewrite_and_state_preserved(self):
        first=self.ready();tid=first['tasks'][0]['id'];self.store.patch(SID,tid,{'note':'original'})
        self.path.write_bytes(record('user','replacement'))
        d=self.ready();self.assertNotEqual(first['generation'],d['generation']);self.assertEqual(d['review_state']['tasks'][tid]['note'],'original')
    def test_corrupt_state_not_overwritten(self):
        self.store.state_path(SID).write_text('broken')
        with self.assertRaises(ValueError):self.store.patch(SID,'tid',{'note':'x'})
        self.assertEqual(self.store.state_path(SID).read_text(),'broken')
    def test_concurrent_build_and_review_updates(self):
        threads=[threading.Thread(target=self.store.manifest,args=(SID,)) for _ in range(12)]
        for t in threads:t.start()
        for t in threads:t.join()
        d=self.ready();self.assertEqual(self.store.metrics['builds'],1);tid=d['tasks'][0]['id']
        threads=[threading.Thread(target=self.store.patch,args=(SID,tid,{flag:True})) for flag in ('marked','important','reviewed','later')]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertTrue(all(self.store.load_state(SID)['tasks'][tid][flag] for flag in ('marked','important','reviewed','later')))
    def test_markdown_and_symlink_write_guard(self):
        self.path.unlink();p=self.rt['exports']/('codex-session-'+SID+'-2026-1020-0000.md')
        p.write_text('## User\nquestion\n## Assistant\nanswer needle\n',encoding='utf-8');self.store.scan(True)
        d=self.ready();tid=d['tasks'][0]['id'];self.assertIn('answer',self.store.section(SID,tid,1)['text'])
        self.assertEqual(self.store.search(SID,'needle')['total'],1)
        target=self.store.state_path(SID);target.unlink();target.symlink_to(self.path)
        with self.assertRaises(ValueError):NS['atomic'](target,{'bad':True})
        self.assertFalse(self.path.exists())

if __name__=='__main__':unittest.main()
