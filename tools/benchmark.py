"""Read-only HTTP measurements; results do not represent browser paint time."""
import argparse, json, math, statistics, time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import urlopen

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('url');p.add_argument('session_id');p.add_argument('--query',default='permission denied');p.add_argument('--samples',type=int,default=5);p.add_argument('--output')
    a=p.parse_args();base=a.url.rstrip('/');prefix='/api/session/'+quote(a.session_id,safe='');report={'measurement':'HTTP round trip, not browser paint','samples':max(5,a.samples),'endpoints':{}}
    def request(path):
        start=time.monotonic()
        with urlopen(base+path,timeout=90) as r:data=r.read()
        return data,(time.monotonic()-start)*1000
    for name,path in [('health','/api/health'),('sessions','/api/sessions'),('shell','/session/'+quote(a.session_id,safe='')),('manifest',prefix+'/manifest')]:
        samples=[]
        for _ in range(report['samples']):
            raw,ms=request(path);samples.append(ms)
        report['endpoints'][name]={'median_ms':round(statistics.median(samples),2),'p95_ms':round(sorted(samples)[math.ceil(len(samples)*.95)-1],2),'response_bytes':len(raw)}
        if name=='health':report['health']=json.loads(raw)
        if name=='sessions':report['session_count']=len(json.loads(raw))
        if name=='manifest':manifest=json.loads(raw)
    if manifest.get('state')!='ready':raise SystemExit('Manifest not ready; wait for preparation, then benchmark again')
    tasks=manifest['tasks'];report['task_count']=len(tasks)
    task=tasks[min(631,len(tasks)-1)] if tasks else None
    if task:
        raw,ms=request(prefix+'/task/'+task['id']);report['representative_task']={'number':task['n'],'structure_ms':round(ms,2),'sections':len(json.loads(raw)['sections'])}
    u=prefix+'/search?'+urlencode({'q':a.query,'client':'benchmark'})
    for name in ('search_first','search_repeat'):
        raw,ms=request(u);result=json.loads(raw);report[name]={'http_ms':round(ms,2),'server_ms':result.get('elapsed_ms'),'cached':result.get('cached',False),'matching_records':result.get('total')}
    text=json.dumps(report,indent=2);print(text)
    if a.output:Path(a.output).write_text(text+'\n')
if __name__=='__main__':main()
