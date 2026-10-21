"""Artifact reader contracts: no scans, no source writes, explicit roots and static HTML."""
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from urllib.parse import quote, urlencode
from http.server import ThreadingHTTPServer
import test_fast as fixtures

NS=fixtures.NS

class DocumentTests(unittest.TestCase):
    def setUp(self):
        fixtures.FastTests.setUp(self)
        self.reports_tmp=tempfile.TemporaryDirectory();self.root=Path(self.reports_tmp.name).resolve()
        self.md=self.root/'报告 (final).md';self.md.write_text('# Report\n\n**Result**\n\n[Gallery](index.html)\n',encoding='utf-8')
        self.html=self.root/'index.html';self.html.write_text('<h1>Report</h1><img src="chart.png"><script>BAD_SCRIPT</script>',encoding='utf-8')
        self.app=NS['App'](self.store,[str(self.root)])
        self.server=ThreadingHTTPServer(('127.0.0.1',0),self.app.handler())
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        self.reports_tmp.cleanup();fixtures.FastTests.tearDown(self)
    def get(self,path):
        c=http.client.HTTPConnection(*self.server.server_address,timeout=5);c.request('GET',path)
        r=c.getresponse();body=r.read();status=r.status;headers=dict(r.getheaders());c.close();return status,body,headers
    def api(self,path,**extra):return self.get('/api/file?'+urlencode(dict(path=str(path),**extra)))
    def test_opt_in_and_no_eager_report_or_manifest_reads(self):
        disabled=NS['ReportFiles'](self.home)
        with self.assertRaises(NS['ReportError']):disabled.read(str(self.md))
        before=self.path.read_bytes();mtime=self.md.stat().st_mtime_ns
        with mock.patch.object(self.store,'manifest',side_effect=AssertionError('No indexing for report reading')):
            self.assertEqual(self.get('/session/'+fixtures.SID)[0],200)
            self.assertEqual(self.get('/file?'+urlencode({'path':str(self.md)}))[0],200)
            self.assertEqual(self.app.files.bytes_read,0)
            status,body,_=self.api(self.md);self.assertEqual(status,200)
            d=json.loads(body);self.assertEqual(d['kind'],'markdown');self.assertIn('**Result**',d['text'])
        self.assertEqual(self.store.metrics['manifest_bytes'],0)
        self.assertEqual(self.path.read_bytes(),before);self.assertEqual(self.md.stat().st_mtime_ns,mtime)
    def test_relative_session_paths_use_only_bounded_session_meta(self):
        self.path.write_bytes((json.dumps({'type':'session_meta','payload':{'cwd':str(self.root)}})+'\n').encode()+fixtures.record('user','report'))
        status,body,_=self.api(self.md.name,sid=fixtures.SID);self.assertEqual(status,200);self.assertEqual(json.loads(body)['path'],str(self.md))
        self.assertEqual(self.store.metrics['manifest_bytes'],0)
        self.assertEqual(self.api(self.md.name)[0],400)
    def test_forbidden_paths_symlinks_special_files_and_limits(self):
        self.assertEqual(self.api('/etc/passwd')[0],403)
        self.assertEqual(self.api(self.path)[0],403)
        hidden=self.root/'.secret.md';hidden.write_text('private')
        self.assertEqual(self.api(hidden)[0],403)
        (self.root/'auth.json').write_text('secret');self.assertEqual(self.api(self.root/'auth.json')[0],415)
        link=self.root/'link.md';link.symlink_to(self.md);self.assertEqual(self.api(link)[0],403)
        directory=self.root/'redirect';directory.symlink_to(self.root,target_is_directory=True)
        self.assertEqual(self.api(directory/self.md.name)[0],403)
        fifo=self.root/'pipe.md';os.mkfifo(str(fifo));self.assertEqual(self.api(fifo)[0],403)
        large=self.root/'large.md'
        with large.open('wb') as out:out.truncate(2*1024*1024+1)
        self.assertEqual(self.api(large)[0],413)
        self.assertEqual(self.api(self.root/'missing.md')[0],404)
        self.assertEqual(self.get('/files/raw/0/../outside.md')[0],403)
        self.assertEqual(self.get('/files/raw/9/index.html')[0],404)
    def test_static_html_has_sandbox_and_local_resource_routes(self):
        text='''<base href="https://evil.example/"><meta http-equiv="refresh" content="0;url=https://evil.example"><h1 onclick="BAD_EVENT">Report</h1><script>BAD_SCRIPT</script><iframe src="/api/health">BAD_FRAME</iframe><form action="/api/state"><input value="secret"></form><img src="chart.png" onerror="BAD_IMAGE"><link rel="stylesheet" href="theme.css"><a href="https://evil.example/">External</a><a href="next.html">Next</a><style>p{color:red}</style>&lt;script&gt;TEXT&lt;/script&gt;'''
        self.html.write_text(text)
        status,body,h=self.get('/files/raw/0/index.html');text=body.decode()
        self.assertEqual(status,200);self.assertIn('sandbox',h['Content-Security-Policy']);self.assertIn("script-src 'none'",h['Content-Security-Policy']);self.assertIn("connect-src 'none'",h['Content-Security-Policy'])
        for value in ('BAD_SCRIPT','BAD_FRAME','BAD_EVENT','BAD_IMAGE','<script>','<iframe','<base','<form','<input','<meta http-equiv','https://evil.example'):
            self.assertNotIn(value,text)
        self.assertIn('src="/files/raw/0/chart.png"',text);self.assertIn('href="/files/raw/0/theme.css"',text)
        self.assertIn('href="/file?path=',text);self.assertIn('next.html" target="_top"',text);self.assertIn('&lt;script&gt;TEXT&lt;/script&gt;',text)
        wrapper=self.get('/file?'+urlencode({'path':str(self.html)}))[1].decode();self.assertIn('sandbox="allow-top-navigation-by-user-activation"',wrapper)
        self.assertNotIn('allow-scripts',wrapper);self.assertNotIn('allow-same-origin',wrapper)
        image=self.root/'chart.png';image.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        status,body,h=self.get('/files/raw/0/chart.png');self.assertEqual(status,200);self.assertEqual(body,image.read_bytes());self.assertEqual(h['Content-Type'],'image/png')
    def test_encoded_paths_and_invalid_text(self):
        d=json.loads(self.api(self.md)[1]);self.assertEqual(self.get(d['raw_url'])[0],200)
        nested=self.root/'子目录';nested.mkdir();(nested/'index.html').write_text('<img src="../chart.png"><img src="../../outside.png"><img src="https://evil.example/a.png">')
        raw='/files/raw/0/'+quote('子目录/index.html');text=self.get(raw)[1].decode()
        self.assertIn('/files/raw/0/chart.png',text);self.assertNotIn('outside.png',text);self.assertNotIn('evil.example',text)
        self.md.write_bytes(b'\xff\xfe');self.assertEqual(self.api(self.md)[0],415)
    def test_file_root_is_preserved_in_daemon_child(self):
        args=NS['parser']().parse_args(['serve','--codex-home',str(self.home),'--file-root',str(self.root),'--file-root',str(self.root)])
        self.assertEqual(args.file_root,[str(self.root),str(self.root)])
        with mock.patch.dict(NS,{'__file__':str(Path('codexview').resolve()),'read_pid':mock.Mock(side_effect=[None,12345,12345]),'owned_open':mock.mock_open()}), mock.patch.object(NS['subprocess'],'Popen') as popen, mock.patch.object(NS['time'],'sleep'):
            NS['daemon'](args)
            command=popen.call_args[0][0]
            self.assertEqual(command.count('--file-root'),2)
            positions=[i for i,x in enumerate(command) if x=='--file-root']
            self.assertEqual([command[i+1] for i in positions],[str(self.root),str(self.root)])

    def test_report_navigation_preserves_context_and_blocks_escapes(self):
        self.html.write_text('<a href="next.html#results">Next</a><a href="#same">Same</a><a href="../outside.html">Outside</a><a href="//evil.example/report.html">Remote</a>')
        status,raw,h=self.get('/files/raw/0/index.html?'+urlencode({'sid':fixtures.SID,'task':'733'}))
        text=raw.decode();self.assertEqual(status,200)
        self.assertIn('sid='+fixtures.SID,text);self.assertIn('task=733',text);self.assertIn('#results',text)
        self.assertIn('href="#same"',text);self.assertEqual(text.count('target="_top"'),1)
        self.assertNotIn('outside.html',text);self.assertNotIn('evil.example',text)
        self.assertIn("script-src 'none'",h['Content-Security-Policy']);self.assertIn('sandbox allow-top-navigation-by-user-activation',h['Content-Security-Policy'])
        self.assertEqual(NS['report_task']('733'),'733');self.assertEqual(NS['report_task']('1#evil'),'')
        wrapper=NS['document_html']('</script>','fixture','733')
        self.assertNotIn('"path": "</script>"',wrapper)
        self.assertIn('"task": "733"',wrapper)

    def test_image_reader_and_bounded_html_image_list(self):
        image=self.root/'chart.png';image.write_bytes(b'\x89PNG\r\n\x1a\nfixture');before=image.read_bytes()
        status,body,_=self.api(image);self.assertEqual(status,200);data=json.loads(body);self.assertEqual(data['kind'],'image');self.assertEqual(data['text'],'');self.assertEqual(self.get(data['raw_url'])[1],before)
        data=json.loads(self.api(self.html,sid=fixtures.SID,task='1')[1]);self.assertEqual(len(data['images']),1);self.assertIn('chart.png',data['images'][0]);self.assertIn('task=1',data['images'][0])
        wrapper=self.get('/file?'+urlencode({'path':str(image),'from':str(self.html),'sid':fixtures.SID,'task':'1'}))[1].decode();self.assertIn('fileImages',wrapper);self.assertIn('chart.png',wrapper)
        self.assertEqual(image.read_bytes(),before)
        self.html.write_text('<img src="../../outside.png"><img src="https://evil.example/image.png">');self.assertEqual(json.loads(self.api(self.html)[1])['images'],[])
