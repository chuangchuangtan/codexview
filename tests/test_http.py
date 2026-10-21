"""HTTP contract tests against an isolated synthetic CODEX_HOME."""
import http.client, json, threading, time, unittest
from http.server import ThreadingHTTPServer
import test_fast as fixtures
NS=fixtures.NS
SID=fixtures.SID
record=fixtures.record

class HttpTests(unittest.TestCase):
    ready=fixtures.FastTests.ready
    # Reuse synthetic fixture setup without inheriting its test cases.
    def setUp(self):
        fixtures.FastTests.setUp(self)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),NS['App'](self.store).handler())
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        # Wait for any manifest worker before deleting the isolated fixture.
        for _ in range(100):
            if all(j.get('state') not in ('queued','indexing') for j in self.store.jobs.values()):break
            time.sleep(.01)
        fixtures.FastTests.tearDown(self)
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection(*self.server.server_address,timeout=5)
        c.request(method,path,body,headers or {});r=c.getresponse();raw=r.read();status=r.status;h=dict(r.getheaders());c.close()
        return status,raw,h
    def test_write_origin_size_and_validation(self):
        d=self.ready();tid=d['tasks'][0]['id'];url='/api/session/'+SID+'/task/'+tid
        status,_,_=self.request('POST',url,'{"important":true}',{'Origin':'http://evil.example'})
        self.assertEqual(status,403);self.assertFalse(self.store.load_state(SID)['tasks'].get(tid,{}).get('important'))
        self.assertEqual(self.request('POST',url,'x'*65537)[0],413)
        self.assertEqual(self.request('POST',url,'[]')[0],400)
        self.assertEqual(self.request('POST',url,'{"note":"saved"}',{'Content-Type':'application/json'})[0],200)
        self.assertEqual(self.store.load_state(SID)['tasks'][tid]['note'],'saved')
        self.assertEqual(self.request('POST','/api/session/'+SID+'/task/unknown','{}')[0],400)
    def test_shell_headers_and_script_escaping(self):
        status,raw,h=self.request('GET','/session/'+SID)
        self.assertEqual(status,200);self.assertEqual(self.store.metrics['manifest_bytes'],0)
        self.assertEqual(h['X-Content-Type-Options'],'nosniff');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
        dangerous='</script><script>alert(1)</script>'
        rendered=NS['workspace_html'](SID,{'adapter':'native-jsonl','tasks':[]},{'tasks':{},'note':dangerous},[],[])
        self.assertNotIn(dangerous,rendered)
        self.assertEqual(self.request('GET','/api/health')[0],200)
    def test_review_flags_and_notes_persist_without_source_writes(self):
        d=self.ready();tid=d['tasks'][0]['id'];url='/api/session/'+SID+'/task/'+tid
        source=self.path.read_bytes();stamp=self.path.stat().st_mtime_ns
        for key in ('important','marked','later','reviewed'):
            status,body,_=self.request('POST',url,json.dumps({key:True}),{'Content-Type':'application/json'})
            self.assertEqual(status,200);self.assertTrue(json.loads(body)['state']['tasks'][tid][key])
        self.request('POST',url,json.dumps({'note':'Review note'}))
        fresh=NS['Store'](self.home,self.rt,[]);state=fresh.load_state(SID)['tasks'][tid]
        self.assertEqual(state['note'],'Review note');self.assertTrue(all(state[k] for k in ('important','marked','later','reviewed')))
        self.assertEqual(self.path.read_bytes(),source);self.assertEqual(self.path.stat().st_mtime_ns,stamp)
    def test_deep_hit_focus_cache_and_append_invalidation(self):
        with self.path.open('ab') as f:f.write(record('assistant','x'*300000+'deepneedle'))
        d=self.ready();tid=d['tasks'][0]['id'];result=self.store.search(SID,'deepneedle');before=self.store.metrics['search_bytes']
        again=self.store.search(SID,'deepneedle');self.assertTrue(again['cached']);self.assertEqual(before,self.store.metrics['search_bytes'])
        url='/api/session/'+SID+'/task/'+tid+'/section/2?focus=deepneedle'
        status,raw,_=self.request('GET',url);self.assertEqual(status,200);data=json.loads(raw)
        self.assertIn('deepneedle',data['text']);self.assertGreater(data['text_offset'],262144);self.assertLess(len(data['text']),262145)
        with self.path.open('ab') as f:f.write(record('assistant','deepneedle again'))
        self.ready();self.assertEqual(self.store.search(SID,'deepneedle')['total'],2)
    def test_runtime_file_symlinks_are_readonly(self):
        before=self.path.read_bytes()
        for target in (self.rt['log'],self.rt['pid']):

            if target.exists():target.unlink()
            target.symlink_to(self.path)
            with self.assertRaises(ValueError):NS['owned_open'](target,append=True)
            target.unlink()
        self.assertEqual(self.path.read_bytes(),before)

    def test_task_timestamp_from_original_user_record(self):
        first=json.loads(record('user','Dated task'));first['timestamp']='2026-10-16T02:34:56.000Z'
        self.path.write_bytes((json.dumps(first)+'\n').encode()+record('assistant','answer'))
        d=self.ready();tid=d['tasks'][0]['id'];before=self.path.read_bytes()
        status,body,_=self.request('GET','/api/session/'+SID+'/task/'+tid)
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['started_at'],first['timestamp'])
        self.assertEqual(self.path.read_bytes(),before)

    def test_watch_and_search_cache_http_boundaries(self):
        before=self.store.metrics.copy();status,body,_=self.request('GET','/api/session/'+SID+'/watch');self.assertEqual(status,200);self.assertIn('token',json.loads(body));self.assertEqual(self.store.metrics,before)
        self.assertEqual(self.request('GET','/api/session/'+SID+'/related')[0],200)
        url='/api/session/'+SID+'/search-cache';self.assertFalse(json.loads(self.request('GET',url)[1])['ready']);self.assertEqual(self.request('POST',url,'{}',{'Origin':'http://evil.example'})[0],403);self.assertEqual(self.store.search_builds,{})
        self.ready();self.assertEqual(self.request('POST',url,'{}')[0],200)
        for _ in range(200):
            if self.store.search_cache_status(SID)['state'] not in ('queued','building'):break
            time.sleep(.01)
        self.assertTrue(json.loads(self.request('GET',url)[1])['ready']);self.assertEqual(self.request('POST',url+'/cancel','{}')[0],200)
