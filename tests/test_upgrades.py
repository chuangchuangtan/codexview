"""Read-only watch/lineage and optional search acceleration contracts."""
import hashlib,json,time,unittest
from unittest import mock
import test_fast as fixtures
NS=fixtures.NS;SID=fixtures.SID;record=fixtures.record

class UpgradeTests(unittest.TestCase):
    ready=fixtures.FastTests.ready
    def setUp(self):fixtures.FastTests.setUp(self)
    def tearDown(self):
        for j in self.store.search_builds.values():
            if j.get('cancel'):j['cancel'].set()
        for _ in range(200):
            if all(j.get('state') not in ('queued','building') for j in self.store.search_builds.values()):break
            time.sleep(.01)
        fixtures.FastTests.tearDown(self)
    def cache_ready(self):
        for _ in range(500):
            status=self.store.search_cache_status(SID)
            if status['state']=='ready':return status
            if status['state']=='error':self.fail(status)
            time.sleep(.01)
        self.fail('Search cache timeout')
    def test_watch_uses_only_current_file_stat(self):
        self.ready();before=self.store.metrics.copy()
        with mock.patch.object(self.store,'scan',side_effect=AssertionError('watch must not discover')):
            first=self.store.watch(SID)
            with self.path.open('ab') as f:f.write(record('assistant','new content'))
            second=self.store.watch(SID)
        self.assertNotEqual(first['token'],second['token']);self.assertEqual(self.store.metrics,before)
    def test_declared_parent_and_fork_only(self):
        child='87654321-1234-1234-1234-123456789abc';p=self.path.with_name('rollout-2026-10-20T00-00-01-'+child+'.jsonl')
        header={'type':'session_meta','payload':{'source':{'subagent':{'thread_spawn':{'parent_thread_id':SID,'agent_role':'reviewer'}}}}}
        p.write_bytes((json.dumps(header)+'\n').encode()+record('user','child task'));before=p.read_bytes();self.store.scan(True)
        related=self.store.related(SID);self.assertEqual(related['sessions'][0]['id'],child);self.assertEqual(related['sessions'][0]['relation'],'Child agent');self.assertEqual(related['sessions'][0]['agent_role'],'reviewer')
        self.assertEqual(self.store.related(child)['sessions'][0]['id'],SID);self.assertEqual(p.read_bytes(),before)
        # No title/text heuristic invents relationships.
        p.write_bytes(record('user','parent '+SID));self.assertEqual(self.store.related(SID)['sessions'],[])
    def test_search_cache_semantics_append_and_readonly(self):
        with self.path.open('ab') as f:f.write(record('assistant','中文审核 NEEDLE\nsecond line'))
        self.ready();source=self.path.read_bytes();stamp=self.path.stat().st_mtime_ns
        expected={q:self.store._search(SID,q) for q in ['审核','中文','NEEDLE','not present']}
        self.store.start_search_cache(SID);self.assertTrue(self.cache_ready()['complete'])
        for q,before in expected.items():
            after=self.store._search(SID,q);self.assertEqual(after['matches'],before['matches']);self.assertTrue(after['accelerated'])
        self.assertEqual(self.path.read_bytes(),source);self.assertEqual(self.path.stat().st_mtime_ns,stamp)
        with self.path.open('ab') as f:f.write(record('assistant','中文审核 added'))
        self.ready();self.assertEqual(self.store._search(SID,'审核')['total'],2);self.assertFalse(self.store.search_cache_status(SID)['complete'])
        self.store.start_search_cache(SID);self.assertTrue(self.cache_ready()['complete']);self.assertEqual(self.store._search(SID,'审核')['total'],2)
    def test_partial_corrupt_and_redirected_cache_fallback(self):
        with self.path.open('ab') as f:f.write(record('assistant','target '*100))
        self.ready();expected=self.store._search(SID,'target')['matches']
        with mock.patch.dict(NS,{'SEARCH_CACHE_LIMIT':100}):
            self.store.start_search_cache(SID);status=self.cache_ready()
        self.assertFalse(status['complete']);self.assertEqual(self.store._search(SID,'target')['matches'],expected)
        info=self.store.search_cache_info(SID);data=self.store.search_root()/info['file'];data.write_bytes(b'x'*data.stat().st_size)
        self.assertEqual(self.store._search(SID,'target')['matches'],expected)
        data.unlink();data.symlink_to(self.path);before=self.path.read_bytes();self.assertEqual(self.store._search(SID,'target')['matches'],expected);self.assertEqual(self.path.read_bytes(),before)
    def test_cancellation_keeps_previous_cache(self):
        self.ready();self.store.start_search_cache(SID);self.cache_ready();previous=self.store.search_cache_info(SID)
        with self.path.open('ab') as f:f.write(record('assistant','append'))
        self.ready()
        with self.store.search_build_gate:
            self.store.start_search_cache(SID);self.store.cancel_search_cache(SID)
        for _ in range(100):
            if self.store.search_cache_status(SID)['state']=='cancelled':break
            time.sleep(.01)
        self.assertEqual(self.store.search_cache_info(SID)['file'],previous['file']);self.assertEqual(self.store.search_cache_status(SID)['state'],'cancelled')

    def test_compression_and_oversize_records_preserve_matches(self):
        with self.path.open('ab') as f:
            f.write(record('assistant',('审核 compression target '*3000)))
            f.write(record('assistant','x'*(NS['SEARCH_RECORD_LIMIT']+100)+' overflow needle'))
        self.ready();before={q:self.store._search(SID,q)['matches'] for q in ['compression','审核','overflow needle']}
        self.store.start_search_cache(SID);status=self.cache_ready();self.assertTrue(status['complete'])
        info=self.store.search_cache_info(SID);self.assertLess(info['cache_bytes'],10000)
        for q,expected in before.items():
            result=self.store._search(SID,q);self.assertTrue(result['accelerated']);self.assertEqual(result['matches'],expected)

if __name__=='__main__':unittest.main()
