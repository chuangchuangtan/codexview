const M=JSON.parse(document.querySelector('#model').textContent),T=M.tasks;let S=M.state,F='all',cur=T[0]?.id,mode=localStorage.codexviewMode||'full',q='';const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],st=id=>S.tasks[id]||(S.tasks[id]={});
const readingExplicit=!!location.hash.match(/^#task-\d+$/);
const readingReload=performance.getEntriesByType?.('navigation')?.[0]?.type==='reload';
const readingResumeRequested=new URLSearchParams(location.search).get('resume')==='1';
const initialReading=readBookmark();
function pref(){let th=localStorage.codexviewTheme||localStorage.mdvTheme||'dark',fs=+(localStorage.codexviewFont||localStorage.mdvFont||14);document.documentElement.dataset.theme=th;document.documentElement.style.setProperty('--fs',fs+'px');$('#theme').textContent=th==='dark'?'☀':'☾';$('#mode').title='Toggle execution evidence';$('#mode').textContent=mode==='overview'?'Reading focus':'With activity';$('#reader').classList.toggle('overview',mode==='overview')}
function match(t){let s=st(t.id),txt=(t.title+' '+t.n).toLowerCase();if(q&&!txt.includes(q))return false;return F==='all'||F==='new'&&t.new||F==='important'&&s.important||F==='marked'&&s.marked||F==='later'&&s.later||F==='reviewed'&&s.reviewed}function visible(){return T.filter(match)}
function info(x){let l=x.toLowerCase(),k='Activity',ic='·';if(/traceback|\berror\b|\bfailed\b|exit code [1-9]|permission denied/.test(l)){k='Attention';ic='!'}else if(/apply_patch|patching file/.test(l)){k='Edited files';ic='✎'}else if(/pytest|unittest|npm test|cargo test/.test(l)){k='Ran tests';ic='✓'}else if(/web_search|search_query/.test(l)){k='Searched web';ic='⌕'}else if(/rg |grep |find |ls |cat |sed |head |tail |glob/.test(l)){k='Explored workspace';ic='⌕'}else if(/exec_command|shell|command|^\$ /m.test(l)){k='Ran command';ic='›'}return {k,ic,type:k.toLowerCase().replace(/ /g,'-'),n:x?x.split('\n').length:0}}
function sh(x){if(x.role==='Activity'||x.role==='Reasoning')return `<div class="aitem tool-card" data-i="${x.i}" data-role="${x.role}"><button class="aline tool-head"><span class="tool-icon">·</span><span class="kind">${esc(x.label||x.role)}</span><span class="meta"></span><span class="chev">›</span></button><div class="payload tool-body" hidden></div></div>`;return `<div class="sec ${x.role.toLowerCase()}" data-i="${x.i}" data-role="${x.role}"><div class="payload"><div class="skeleton"><i></i><i></i><i></i></div></div></div>`}
function taskTime(t){if(!t.started_at)return '';let date=new Date(t.started_at);if(Number.isNaN(date.getTime()))return '';let text=new Intl.DateTimeFormat(navigator.language||'en',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(date);return `<time class="task-time" datetime="${esc(t.started_at)}" title="Started: ${esc(t.started_at)} · displayed in your local timezone">${esc(text)}</time>`}
function th(t){let s=st(t.id);return `<section class="task" data-id="${t.id}"><div class="taskhead">TASK #${String(t.n).padStart(3,'0')}${t.new?' · NEW':''}${taskTime(t)}<span class="grow"></span><button class="deep-link" data-link="${t.n}" title="Copy link to task">#</button><span class="marks"><button class="i ${s.important?'on':''}" data-a="important">★ Important</button><details class="review-actions"><summary aria-label="More review actions">${s.marked?'● ':''}${s.later?'◷ ':''}${s.reviewed?'✓ ':''}···</summary><div class="review-pop"><button class="m ${s.marked?'on':''}" data-a="marked">● Marked</button><button class="l ${s.later?'on':''}" data-a="later">◷ Later</button><button class="r ${s.reviewed?'on':''}" data-a="reviewed">✓ Reviewed</button></div></details></span></div><h2>${esc(t.title)}</h2>${sectionMarkup(t)}<details class="notes ${s.note?'has-note':''}"><summary>✎ ${s.note?'Note':'Add note'}</summary><textarea placeholder="Write a private review note…">${esc(s.note||'')}</textarea></details></section>`}
let ctrls=[],token=0;function cancel(){ctrls.forEach(x=>x.abort());ctrls=[]}async function load(x,preview=false,textOffset=0,focus='',replacePage=false){let task=x.closest('.task'),box=x.querySelector('.payload'),ctl=new AbortController();ctrls.push(ctl);try{let r=await fetch(`/api/session/${encodeURIComponent(M.sid)}/task/${task.dataset.id}/section/${x.dataset.i}?offset=${textOffset}${focus?'&focus='+encodeURIComponent(focus):''}`,{signal:ctl.signal}),d=await r.json();if(!r.ok)throw Error();if(preview){let z=info(d.text||''),b=x.querySelector('.aline');b.querySelector('.kind').textContent=z.k;b.querySelector('.tool-icon').textContent=z.ic;b.querySelector('.meta').textContent=z.n?z.n+' lines':'';x.dataset.tool=z.type;let g=x.closest('.ag');if(g){let c={};g.querySelectorAll('.aitem[data-tool]').forEach(n=>c[n.dataset.tool]=(c[n.dataset.tool]||0)+1);let names={'ran-command':'commands','edited-files':'edits','ran-tests':'tests','searched-web':'web','explored-workspace':'explore','attention':'attention','activity':'other'};let parts=Object.entries(c).filter(([k,v])=>v&&k!=='activity').map(([k,v])=>v+' '+(names[k]||k));let z0=g.querySelector('.ag-stats');if(z0)z0.textContent=parts.length?' · '+parts.join(' · '):''}return}if(!box.isConnected)return;let stableAnchor=viewAnchor();let rendered=(x.dataset.role==='User'||x.dataset.role==='Assistant')?'<div class="md" data-page-offset="'+(d.text_offset||0)+'">'+mdRender(d.text||'')+'</div>':'<pre>'+esc(d.text||'')+'</pre>';if(textOffset&&!focus&&!replacePage){box.querySelector('.load-more')?.remove();box.insertAdjacentHTML('beforeend',rendered)}else box.innerHTML=rendered;if(d.next_offset!==null&&d.next_offset!==undefined){let more=document.createElement('button');more.className='btn load-more';more.textContent='Load more content';more.onclick=()=>load(x,false,d.next_offset);box.append(more)}box.dataset.loaded=1;box.dataset.offset=d.text_offset||0;keepView(stableAnchor);collectReports?.(task);}catch(e){if(e.name!=='AbortError'){box.replaceChildren();let error=document.createElement('div');error.className='load-error';error.textContent='This section could not be loaded. ';let retry=document.createElement('button');retry.textContent='Retry';retry.onclick=()=>load(x,false,textOffset,focus);error.append(retry);box.append(error)}}}

function navRow(){if(document.body.classList.contains('sidebar-collapsed'))return 56;let fs=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--fs'))||14;return (document.documentElement.dataset.density==='compact'?Math.max(48,Math.min(70,fs*3.5)):Math.max(58,Math.min(92,fs*4.65)))+8}function side(){let ROW=navRow(),V=visible(),b=$('#tl'),all=T.length,ri=T.reduce((n,t)=>n+(st(t.id).reviewed?1:0),0),ci=Math.max(0,V.findIndex(x=>x.id===cur));if($('#navpos'))$('#navpos').textContent=V.length?(ci+1)+' / '+V.length:'0 / 0';if($('#reviewpct'))$('#reviewpct').textContent=(all?Math.round(ri*100/all):0)+'%';if($('#reviewbar'))$('#reviewbar').style.width=(all?ri*100/all:0)+'%';let h=b.clientHeight||600,top=b.scrollTop,start=Math.max(0,Math.floor(top/ROW)-4),end=Math.min(V.length,start+Math.ceil(h/ROW)+8),rows=V.slice(start,end).map(t=>{let s=st(t.id), badges=`${t.new?'<span class="vbadge new">NEW</span>':''}${s.important?'<span class="vbadge important">★</span>':''}${s.marked?'<span class="vbadge marked">●</span>':''}${s.later?'<span class="vbadge later">LATER</span>':''}${s.reviewed?'<span class="vbadge reviewed">✓</span>':''}`;return `<div role="button" tabindex="0" aria-label="Task ${t.n}: ${esc(t.title)}" aria-current="${t.id===cur?'true':'false'}" class="vrow ${t.id===cur?'cur':''}" data-id="${t.id}" data-attention="${t.attention?1:0}" data-new="${t.new?1:0}" data-important="${s.important?1:0}"><div class="vrail"><span class="vdot"></span></div><div class="vbody"><div class="vmeta"><span class="vnum">TASK ${t.n}</span><span class="vbadges">${badges}</span></div><div class="vtitle">${esc(t.title)}</div></div><svg class="vchev" viewBox="0 0 16 16" aria-hidden="true"><path d="m6 3 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>`}).join('');b.innerHTML=`<div class="vspacer" style="height:${V.length*ROW}px"><div class="vrows" style="transform:translateY(${start*ROW}px)">${rows}</div></div>`;b.scrollTop=top;b.querySelectorAll('.vrow').forEach(x=>{x.onclick=()=>reader(x.dataset.id);x.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();reader(x.dataset.id)}}})}
$$('.filter').forEach(x=>x.onclick=()=>{F=x.dataset.f;$$('.filter').forEach(y=>y.classList.toggle('on',y===x));reader(cur,false)});$('#taskq').oninput=e=>{q=e.target.value.trim().toLowerCase();reader(cur,false)};let sideFrame=0;$('#tl').onscroll=()=>{if(!sideFrame)sideFrame=requestAnimationFrame(()=>{sideFrame=0;side()})};$('#mode').onclick=()=>{mode=mode==='overview'?'full':'overview';localStorage.codexviewMode=mode;pref()};$('#theme').onclick=()=>{localStorage.codexviewTheme=(localStorage.codexviewTheme||localStorage.mdvTheme||'dark')==='dark'?'light':'dark';pref()};function font(d){localStorage.codexviewFont=Math.max(10,Math.min(24,+(localStorage.codexviewFont||14)+d));pref();side()}$('#minus').onclick=()=>font(-1);$('#plus').onclick=()=>font(1);$('#resetfont').onclick=()=>{localStorage.codexviewFont=14;pref();side()};
let searchCtl=null,searchMatches=[],searchAt=-1,searchQuery='';let searchSequence=0;const searchClient=Math.random().toString(36).slice(2);
function markSnippet(text,q){let i=String(text).toLowerCase().indexOf(q.toLowerCase());return i<0?esc(text):esc(text.slice(0,i))+'<mark>'+esc(text.slice(i,i+q.length))+'</mark>'+esc(text.slice(i+q.length))}
function openSessionSearch(){$('#sessionSearchPanel').classList.add('open');setTimeout(()=>$('#sessionSearchInput').focus(),0)}
function closeSessionSearch(){searchSequence++;if(searchCtl){searchCtl.abort();fetch(`/api/session/${encodeURIComponent(M.sid)}/search-cancel?client=${searchClient}`,{method:'POST'})}$('#sessionSearchPanel').classList.remove('open')}
async function runSessionSearch(){const sequence=++searchSequence;let q=$('#sessionSearchInput').value.trim(),scope=$('#sessionSearchScope').value;if(q.length<2){$('#sessionSearchMeta').textContent='Type at least 2 characters';$('#sessionSearchResults').innerHTML='';return}if(searchCtl)searchCtl.abort();searchCtl=new AbortController();searchQuery=q;$('#sessionSearchMeta').innerHTML='<span class="search-spinner"></span>Searching this session…';$('#sessionSearchResults').innerHTML='';try{let u=`/api/session/${encodeURIComponent(M.sid)}/search?q=${encodeURIComponent(q)}&scope=${encodeURIComponent(scope)}&limit=200&client=${searchClient}`,r=await fetch(u,{signal:searchCtl.signal}),d=await r.json();if(sequence!==searchSequence)return;if(!r.ok)throw Error(d.error||'Search failed');searchMatches=d.matches||[];searchAt=searchMatches.length?0:-1;$('#sessionSearchMeta').textContent=`${d.total||0} matching records${searchMatches.length?` in ${new Set(searchMatches.map(x=>x.task_id)).size} tasks`:''}${d.truncated?' · first '+searchMatches.length+' records':''} · ${d.cached?'cached':((d.elapsed_ms||0)/1000).toFixed(1)+' s'}`;$('#sessionSearchResults').innerHTML=searchMatches.length?searchMatches.map((x,i)=>`<button class="sresult ${i===0?'active':''}" data-si="${i}"><span class="sr-top"><b>TASK ${x.task_n}</b><span class="sr-role">${esc(x.role)}</span></span><span class="sr-snippet">${markSnippet(x.snippet,q)}</span></button>`).join(''):'<div class="search-empty">No matches in this session.</div>'}catch(e){if(e.name!=='AbortError'&&sequence===searchSequence)$('#sessionSearchMeta').textContent='Search failed. Press Enter to retry.'}}
let pendingSearchTarget=null;
function clearSearchMarks(root=document){root.querySelectorAll?.('mark.exact-search-hit').forEach(m=>m.replaceWith(document.createTextNode(m.textContent)));root.querySelectorAll?.('.search-target-section').forEach(x=>x.classList.remove('search-target-section'))}

async function gotoSearch(i){let x=searchMatches[i];if(!x)return;pendingSearchTarget={...x,query:searchQuery};closeSessionSearch();F='all';q='';mode='full';$('#taskq').value='';$$('.filter').forEach(b=>b.classList.toggle('on',b.dataset.f==='all'));await reader(x.task_id)}
document.addEventListener('click',async e=>{let sr=e.target.closest('.sresult');if(sr){gotoSearch(+sr.dataset.si);return}let dl=e.target.closest('.deep-link');if(dl){let u=location.origin+location.pathname+'#task-'+dl.dataset.link;copyText(u);return}let b=e.target.closest('.marks button');if(b)return patch(b.closest('.task').dataset.id,{[b.dataset.a]:!st(b.closest('.task').dataset.id)[b.dataset.a]});let l=e.target.closest('.aline');if(l){let x=l.closest('.aitem'),box=x.querySelector('.payload');if(box.hidden){box.hidden=false;if(!box.dataset.loaded)await load(x);l.querySelector('.chev').textContent='⌄'}else{box.hidden=true;l.querySelector('.chev').textContent='›'}}});document.addEventListener('change',e=>{if(e.target.tagName==='TEXTAREA')patch(e.target.closest('.task').dataset.id,{note:e.target.value});if(e.target.id==='ss')location.href='/session/'+encodeURIComponent(e.target.value)});document.addEventListener('keydown',e=>{if(e.target.matches('input,textarea,select'))return;if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='f'){e.preventDefault();openSessionSearch();return}if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openPalette();return}if(e.key==='/'){e.preventDefault();$('#taskq').focus();return}if(e.key==='j')step(1);else if(e.key==='k')step(-1);else if(e.key==='i'&&cur)patch(cur,{important:!st(cur).important});else if(e.key==='m'&&cur)patch(cur,{marked:!st(cur).marked});else if(e.key==='l'&&cur)patch(cur,{later:!st(cur).later});else if(e.key==='r'&&cur)patch(cur,{reviewed:!st(cur).reviewed});else if(e.key==='o')$('#mode').click()});$('#baseline').onclick=async()=>{if(confirm('Mark current session tasks as NEW baseline?')){await fetch(`/api/session/${encodeURIComponent(M.sid)}/baseline`,{method:'POST'});location.reload()}};
function overview(){const count=k=>T.filter(t=>st(t.id)[k]).length;for(let [id,v] of Object.entries({ovTasks:T.length,ovReviewed:count('reviewed'),ovNew:T.filter(t=>t.new).length,ovImportant:count('important'),ovLater:count('later'),ovMarked:count('marked')}))$('#'+id).textContent=v;$('#overviewPanel').classList.add('open')}
function closeOverview(){$('#overviewPanel').classList.remove('open')}
$('#sessionSearchClose').onclick=closeSessionSearch;$('#sessionSearchInput').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();runSessionSearch()}else if(e.key==='Escape')closeSessionSearch()};$('#sessionSearchScope').onchange=()=>{if($('#sessionSearchInput').value.trim().length>=2)runSessionSearch()};$('#sessionSearchPanel').onclick=e=>{if(e.target.id==='sessionSearchPanel')closeSessionSearch()};$('#overviewBtn').onclick=overview;$('#overviewClose').onclick=closeOverview;$('#overviewPanel').onclick=e=>{if(e.target.id==='overviewPanel')closeOverview()};
function taskFromHash(){let m=location.hash.match(/^#task-(\d+)$/);if(!m)return null;let n=+m[1];return T.find(t=>t.n===n)?.id||null}
window.addEventListener('hashchange',()=>{let id=taskFromHash();if(id&&id!==cur)reader(id)});
// v5.6 — continuous virtual reader + design interactions
const ICONS={copy:'<svg viewBox="0 0 24 24"><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></svg>'};
function toast(msg){let x=$('#toast');x.textContent=msg;x.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>x.classList.remove('show'),1800)}
function navUpdate(){let V=visible(),i=V.findIndex(x=>x.id===cur),n=$('#tasknav');if(!n)return;n.querySelector('.navcount').textContent=`${i+1} / ${V.length}`;n.querySelector('[data-nav="prev"]').disabled=i<=0;n.querySelector('[data-nav="next"]').disabled=i>=V.length-1}

function openPalette(){let p=$('#palette');p.classList.add('open');$('#paletteInput').value='';paletteRender('');setTimeout(()=>$('#paletteInput').focus(),0)}function closePalette(){$('#palette').classList.remove('open')}
function paletteRender(v){v=v.toLowerCase();let C=[['Next task','J','next'],['Previous task','K','prev'],['Search session content','⌘ F','contentSearch'],['Search task titles','/','search'],['Jump to latest task','','latest'],['Toggle overview','O','overview'],['Toggle theme','T','theme'],['Important','I','important'],['Mark','M','marked'],['Review later','L','later'],['Reviewed','R','reviewed']].filter(x=>x[0].toLowerCase().includes(v));$('#paletteList').innerHTML=C.map((x,i)=>`<button data-cmd="${x[2]}" class="${i?'':'sel'}"><span>${x[0]}</span><kbd>${x[1]}</kbd></button>`).join('')}
function runCmd(c){closePalette();if(c==='contentSearch')openSessionSearch();else if(c==='latest')jumpToTask(T.length);else if(c==='next')step(1);else if(c==='prev')step(-1);else if(c==='search')$('#taskq').focus();else if(c==='overview')$('#mode').click();else if(c==='theme')$('#theme').click();else if(['important','marked','later','reviewed'].includes(c)&&cur)patch(cur,{[c]:!st(cur)[c]})}
$('#paletteInput').oninput=e=>paletteRender(e.target.value);$('#paletteInput').onkeydown=e=>{if(e.key==='Escape')closePalette();if(e.key==='Enter'){let b=$('#paletteList button.sel')||$('#paletteList button');if(b)runCmd(b.dataset.cmd)}};$('#palette').onclick=e=>{if(e.target.id==='palette')closePalette();let b=e.target.closest('[data-cmd]');if(b)runCmd(b.dataset.cmd)};$('#tasknav').onclick=e=>{let b=e.target.closest('[data-nav]');if(b)step(b.dataset.nav==='next'?1:-1)};
const oldMdRender=mdRender;mdRender=function(src){let h=oldMdRender(src);h=h.replace(/<div class="code-raw" data-lang="([^"]*)"><pre><code>([\s\S]*?)<\/code><\/pre><\/div>/g,(m,lang,body)=>'<div class="code-shell">'+(lang?'<div class="code-label">'+lang+'</div>':'')+'<button class="copy-code" title="Copy code">'+ICONS.copy+'</button><pre><code>'+body+'</code></pre></div>');h=h.replace(/<div class="diff-shell">([\s\S]*?)<pre class="diff"><code>([\s\S]*?)<\/code><\/pre><\/div>/g,(m,label,body)=>'<div class="diff-shell">'+label+'<button class="copy-code" title="Copy diff">'+ICONS.copy+'</button><pre class="diff"><code>'+body+'</code></pre></div>');return h};
document.addEventListener('click',e=>{let b=e.target.closest('.copy-code');if(b){copyText(b.closest('.code-shell,.diff-shell').querySelector('code').innerText)}});
// Explicit navigation and user-scroll intent are separate from layout changes.
let layoutDragging=false,readerBusy=false,suppressScrollUntil=0,userScrollUntil=0,userScrollDir=0,userMotion=0;
function suppressVirtual(ms=600){suppressScrollUntil=performance.now()+ms}
async function reader(id,scroll=true,passive=false){
 $('#taskFilter').value=F;let V=visible(),at=V.findIndex(t=>t.id===id);if(at<0){if(!V.length){$('#reader').textContent='No matching tasks';side();navUpdate();return}at=0;id=V[0].id}
 suppressVirtual(passive?0:600);let oldCurrent=cur,motion=userMotion;cur=id;cancel();proseObserver.disconnect();const tok=++token;readerBusy=true;
 let list=$('#tl'),pitch=navRow();if(oldCurrent!==id||!list.dataset.positioned){side();list.scrollTop=Math.max(0,at*pitch-(list.clientHeight-pitch)/2);list.dataset.positioned='1'}
 side();requestAnimationFrame(()=>{if(tok===token){let list=$('#tl');list.scrollTop=Math.max(0,at*navRow()-(list.clientHeight-navRow())/2);side()}});navUpdate();closeMobileNav();$('#jumpTask').value=V[at].n;$('#jumpTask').max=T.length;
 history.replaceState(null,'','#task-'+V[at].n);
 const ensure=t=>ensureTaskMetadata(t,tok),append=t=>newTaskNode(t);
 try{
  await ensure(V[at]);if(tok!==token)return;
  let W=V.slice(Math.max(0,at-1),at+2);trimTaskWindow(W,scroll&&!readingInitial);
  let current=$(`.task[data-id="${CSS.escape(id)}"]`);
  if(!current){current=append(V[at]);insertTask(current,V[at],W)}
  observeChunks(current);
  pref();if(scroll)current.scrollIntoView({block:'start',behavior:'instant'});
  $('#count').textContent=`${at+1} / ${V.length}`;
  // Reveal the requested search payload before fetching adjacent Task metadata.
  let searchTarget=pendingSearchTarget?.task_id===id?pendingSearchTarget:null;
  if(searchTarget)pendingSearchTarget=null;
  await hydrate(current,tok);
  if(searchTarget&&tok===token)await revealSearchTarget(searchTarget);
  for(let t of W){if(tok!==token)return;if(t.id===id)continue;await ensure(t);if(tok!==token)return;
   let n=$(`.task[data-id="${CSS.escape(t.id)}"]`);if(n)continue;
   n=append(t);insertTask(n,t,W);observeChunks(n);
   // Neighbor placeholders are hydrated only as they enter the viewport.
  }
  await restoreBookmark(current,tok);
  observeProse();scheduleGeometry();if(scroll&&!searchTarget&&tok===token&&motion===userMotion)current.scrollIntoView({block:'start',behavior:'instant'});
 }catch(e){if(e.name!=='AbortError'&&tok===token){$('#reader').textContent='Could not load this task. ';let retry=document.createElement('button');retry.className='btn';retry.textContent='Retry';retry.onclick=()=>reader(id,scroll);$('#reader').append(retry)}}
 finally{if(tok===token){readerBusy=false;suppressVirtual(passive?0:600);updateReadingContext?.()}}
}

const inflightPayloads=new WeakMap();
async function hydrate(root,tok){
 let nodes=[...root.querySelectorAll('.sec.user,.sec.assistant')],i=0;
 async function worker(){while(i<nodes.length&&tok===token){let n=nodes[i++],box=n.querySelector('.payload');if(box.dataset.loaded)continue;let pending=inflightPayloads.get(box);if(!pending){pending=load(n);inflightPayloads.set(box,pending)}try{await pending}finally{inflightPayloads.delete(box)}}}
 await Promise.all(Array.from({length:Math.min(3,nodes.length)},worker));
}
const proseObserver=new IntersectionObserver(entries=>{for(let e of entries)if(e.isIntersecting){proseObserver.unobserve(e.target);hydrate(e.target,token)}},{rootMargin:'900px'});
function observeProse(){$$('.task').forEach(n=>{if(n.dataset.id!==cur)proseObserver.observe(n)})}

// Layout and programmatic search scrolling must never start Task navigation.
let shiftBusy=false;
async function shiftVirtual(dir){
 if(shiftBusy||readerBusy||layoutDragging||performance.now()<suppressScrollUntil)return;
 let V=visible(),at=V.findIndex(t=>t.id===cur),next=V[at+dir];if(!next)return;
 let anchor=$(`.task[data-id="${CSS.escape(next.id)}"]`);if(!anchor)return;
 shiftBusy=true;
 try{await reader(next.id,false,true)}
 finally{shiftBusy=false;checkUserBoundary()}
}
window.addEventListener('wheel',e=>{if(e.target.closest('.side,.session-search-panel,.palette-card,pre'))return;userMotion++;userScrollDir=Math.sign(e.deltaY);userScrollUntil=performance.now()+600;checkUserBoundary()},{passive:true});
let touchReadingY=null;
window.addEventListener('touchstart',e=>{touchReadingY=e.target.closest('.side,.session-search-panel,.palette-card,pre')?null:e.touches[0]?.clientY},{passive:true});
window.addEventListener('touchmove',e=>{let y=e.touches[0]?.clientY;if(touchReadingY==null||y==null)return;let delta=touchReadingY-y;touchReadingY=y;if(Math.abs(delta)>1){userMotion++;userScrollDir=Math.sign(delta);userScrollUntil=performance.now()+1500;checkUserBoundary()}},{passive:true});
window.addEventListener('keydown',e=>{if(e.target.matches('input,textarea,select'))return;if(['PageDown','ArrowDown',' '].includes(e.key)){userMotion++;userScrollDir=1;userScrollUntil=performance.now()+600}else if(['PageUp','ArrowUp'].includes(e.key)){userMotion++;userScrollDir=-1;userScrollUntil=performance.now()+600}});
let boundaryFrame=0;
function checkUserBoundary(){if(boundaryFrame)return;boundaryFrame=requestAnimationFrame(()=>{boundaryFrame=0;if(layoutDragging||readerBusy||performance.now()<suppressScrollUntil||performance.now()>userScrollUntil)return;let n=$(`.task[data-id="${CSS.escape(cur||'')}"]`);if(!n)return;let r=n.getBoundingClientRect();preloadTaskEdge(userScrollDir);if(userScrollDir>0&&r.bottom<readerTop()+80)shiftVirtual(1);else if(userScrollDir<0&&r.top>readerTop()+40)shiftVirtual(-1)})}
window.addEventListener('scroll',checkUserBoundary,{passive:true});

function markExact(root,q){
 if(!root||!q)return null;let needle=q.toLocaleLowerCase();
 let walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),n,bytes=0;
 // Highlight one visible hit with a strict work budget, rather than rebuilding all text nodes.
 while((n=walker.nextNode())&&bytes<524288){bytes+=n.length;if(n.parentElement?.closest('button,script,style'))continue;let at=n.nodeValue.toLocaleLowerCase().indexOf(needle);if(at<0)continue;
  let hit=n.splitText(at);hit.splitText(q.length);let mark=document.createElement('mark');mark.className='exact-search-hit current';hit.replaceWith(mark);mark.append(hit);return mark}
 return null;
}
async function revealSearchTarget(x){
 let task=$(`.task[data-id="${CSS.escape(x.task_id)}"]`),model=T.find(t=>t.id===x.task_id);if(!task||!model)return;
 let si=x.section;if(x.record_start!==undefined)si=model.sections.findIndex(s=>(s.parts||[]).some(p=>p[0]===x.record_start)||s.record_start===x.record_start);
 let sec=ensureSection(task,si);if(!sec)return;
 clearSearchMarks(task);let ag=sec.closest('.ag');if(ag)ag.open=true;
 let box=sec.querySelector('.payload');box.hidden=false;
 await load(sec,false,0,x.query||searchQuery);
 sec.querySelector('.chev')?.replaceChildren(document.createTextNode('⌄'));
 let hit=markExact(box,x.query||searchQuery);sec.classList.add('search-target-section');
 suppressVirtual(1200);(hit||sec).scrollIntoView({block:'center',behavior:'instant'});
}

let geometryFrame=0,sidebarDesired=Number(localStorage.codexviewSidebarWidth)||320,contentDesired=Number(localStorage.codexviewContentWidth)||980;
const sidebarClamp=n=>Math.max(236,Math.min(520,Math.min(innerWidth>900?innerWidth-420:520,n)));
function scheduleGeometry(){if(geometryFrame)return;geometryFrame=requestAnimationFrame(()=>{geometryFrame=0;let reader=$('#reader'),rect=reader.getBoundingClientRect(),handle=$('#contentResizer');handle.style.left=rect.right+'px';$('#contentWidthPill').style.left=(rect.right+12)+'px';handle.setAttribute('aria-valuenow',Math.round(rect.width));$('#sideResizer').setAttribute('aria-valuenow',Math.round($('.side').getBoundingClientRect().width))})}
function applySidebar(n){sidebarDesired=sidebarClamp(n);document.documentElement.style.setProperty('--sidebar',sidebarDesired+'px');scheduleGeometry()}
function applyContent(n){contentDesired=Math.max(480,Math.min(1400,n));document.documentElement.style.setProperty('--content-width',contentDesired+'px');scheduleGeometry();return contentDesired}
function initWidths(){
 const root=document.documentElement,body=document.body,sideHandle=$('#sideResizer'),contentHandle=$('#contentResizer'),pill=$('#contentWidthPill');
 document.documentElement.dataset.density=localStorage.codexviewDensity==='compact'?'compact':'standard';
 $('#readerDensity').value=document.documentElement.dataset.density;
 $('#readerWidth').value=['comfortable','wide'].includes(localStorage.codexviewWidthPreset)?localStorage.codexviewWidthPreset:'custom';
 applySidebar(sidebarDesired);applyContent(contentDesired);
 if(localStorage.codexviewSidebarCollapsed==='1')body.classList.add('sidebar-collapsed');
 $('#sidecollapse').onclick=()=>{suppressVirtual();body.classList.toggle('sidebar-collapsed');localStorage.codexviewSidebarCollapsed=body.classList.contains('sidebar-collapsed')?'1':'0';side();scheduleGeometry()};
 function drag(handle,move,save){let active=null,frame=0,pending=0;
  handle.addEventListener('pointerdown',e=>{if(innerWidth<=900)return;e.preventDefault();active={id:e.pointerId,x:e.clientX,width:$('#reader').getBoundingClientRect().width};layoutDragging=true;suppressVirtual();handle.setPointerCapture(e.pointerId);handle.classList.add('dragging');body.classList.add('layout-dragging');if(handle===contentHandle)pill.style.display='block'});
  handle.addEventListener('pointermove',e=>{if(!active)return;pending=e.clientX;if(frame)return;frame=requestAnimationFrame(()=>{frame=0;if(active)move(pending,active)})});
  function finish(e){if(!active)return;if(frame){cancelAnimationFrame(frame);frame=0;move(pending,active)}active=null;layoutDragging=false;suppressVirtual();handle.classList.remove('dragging');body.classList.remove('layout-dragging');pill.style.display='none';try{handle.releasePointerCapture(e.pointerId)}catch(_){}save();side();scheduleGeometry()}
  handle.addEventListener('pointerup',finish);handle.addEventListener('pointercancel',finish);handle.addEventListener('lostpointercapture',finish);
 }
 drag(sideHandle,x=>applySidebar(x),()=>localStorage.codexviewSidebarWidth=Math.round(sidebarDesired));
 $('#readerDensity').onchange=e=>{suppressVirtual();root.dataset.density=e.target.value;localStorage.codexviewDensity=e.target.value;let list=$('#tl'),at=visible().findIndex(t=>t.id===cur);list.scrollTop=Math.max(0,at*navRow()-(list.clientHeight-navRow())/2);side();scheduleGeometry()};
 $('#readerWidth').onchange=e=>{suppressVirtual();let v=e.target.value;if(v!=='custom')applyContent(v==='wide'?1200:900);localStorage.codexviewWidthPreset=v;localStorage.codexviewContentWidth=Math.round(contentDesired)};
 drag(contentHandle,(x,a)=>{applyContent(a.width+2*(x-a.x));pill.textContent=Math.round($('#reader').getBoundingClientRect().width)+' px'},()=>{localStorage.codexviewContentWidth=Math.round(contentDesired);localStorage.codexviewWidthPreset='custom';$('#readerWidth').value='custom'});
 sideHandle.ondblclick=()=>{applySidebar(320);localStorage.codexviewSidebarWidth=320;side()};
 contentHandle.ondblclick=()=>{applyContent(980);localStorage.removeItem('codexviewContentWidth')};
 sideHandle.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home'].includes(e.key))return;e.preventDefault();applySidebar(e.key==='Home'?320:sidebarDesired+(e.key==='ArrowRight'?16:-16));localStorage.codexviewSidebarWidth=Math.round(sidebarDesired);side()};
 contentHandle.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home'].includes(e.key))return;e.preventDefault();applyContent(e.key==='Home'?980:$('#reader').getBoundingClientRect().width+(e.key==='ArrowRight'?32:-32));localStorage.codexviewContentWidth=Math.round(contentDesired)};
 new ResizeObserver(scheduleGeometry).observe($('.main'));
 new ResizeObserver(scheduleGeometry).observe($('#reader'));
 window.addEventListener('resize',()=>{suppressVirtual();scheduleGeometry();side()});scheduleGeometry();
}
initWidths();

$('#helpbtn').onclick=()=>$('#helpmodal').classList.add('open');$('#helpclose').onclick=()=>$('#helpmodal').classList.remove('open');$('#helpmodal').onclick=e=>{if(e.target.id==='helpmodal')e.currentTarget.classList.remove('open')};document.addEventListener('keydown',e=>{if(e.key==='Escape')$('#helpmodal').classList.remove('open')});pref();
let manifestGeneration=null,refreshBusy=false,lastReadiness='';
async function refreshManifest(retry=false){if(refreshBusy)return;let resume=null;if(!readingBoot){saveReadingPosition();resume=readBookmark()}refreshBusy=true;let again=false;try{
 let r=await fetch(`/api/session/${encodeURIComponent(M.sid)}/manifest${retry?'?retry=1':''}`),d=await r.json();if(!r.ok||d.error){$('#readinessText').textContent='Preparation failed · use Refresh to retry';$('#reader').textContent=d.error||'Cannot prepare session';$('#refreshSession').textContent='Retry';return}
 lastReadiness=d.state;$('#readinessText').textContent=d.state==='ready'?`${d.tasks.length} tasks · On-demand evidence`:`Preparing ${Math.round((d.indexed_bytes||0)/1048576)} / ${Math.round((d.source_bytes||0)/1048576)} MB`;$('#sessionReady b').textContent=M.adapter==='markdown'?'● Markdown source':'● Native source';$('#refreshSession').textContent=d.state==='ready'?'↻ Refresh':`Preparing ${Math.round((d.indexed_bytes||0)/1048576)} / ${Math.round((d.source_bytes||0)/1048576)} MB`;
 if(d.tasks?.length){let oldTail=T[T.length-1]?.id,existing=new Map(T.map(t=>[t.id,t]));let same=manifestGeneration===d.generation;
  T.splice(0,T.length,...d.tasks.map(t=>{let old=same?existing.get(t.id):null;return old?{...t,sections:old.sections,started_at:old.started_at,loaded:old.loaded}:t}));manifestGeneration=d.generation;S=d.review_state;
  // The last task can grow; invalidate only its local metadata on explicit refresh.
  let invalid=new Set([oldTail,T[T.length-1].id]);for(let t of T)if(invalid.has(t.id))t.loaded=false;
  if(!same)$('#reader').replaceChildren();else for(let id of invalid)if(id)$(`.task[data-id="${CSS.escape(id)}"]`)?.remove();
  let requested=taskFromHash(),saved=readingBoot&&initialReading?T.find(t=>t.id===initialReading.task):null;
  let selected=(readingReload&&saved?.id)||requested||(!readingExplicit&&saved?.id)||cur||T[T.length-1].id;
  if(!readingBoot&&resume&&same&&selected===resume.task)readingInitial=resume;
  if(!readingBoot&&followLatest){selected=T[T.length-1].id;readingInitial=null}
  if(readingBoot&&saved&&selected===saved.id&&(!initialReading.generation||initialReading.generation===d.generation)&&(!readingExplicit||readingReload||readingResumeRequested))readingInitial=initialReading;
  await reader(selected,(readingBoot&&!readingInitial)||(!readingBoot&&followLatest));readingBoot=false;acceptSourceToken(d.source_token);
 }else if(d.state==='ready')$('#reader').textContent='No readable user tasks in this session';
 again=['queued','indexing'].includes(d.state);
 }catch(e){$('#readinessText').textContent='Connection interrupted · use Refresh to reconnect';if(!T.length)$('#reader').textContent='Connection failed. Use Refresh to retry.'}finally{refreshBusy=false;if(again)setTimeout(refreshManifest,500)}}

async function copyText(text){try{if(!navigator.clipboard?.writeText)throw Error('Clipboard unavailable');await navigator.clipboard.writeText(text);toast('Copied to clipboard')}catch(_){toast('Clipboard unavailable. Use your browser copy command.')}}
function closeMobileNav(){document.body.classList.remove('mobile-nav-open');$('#mobileNav').setAttribute('aria-expanded','false')}
function openMobileNav(){document.body.classList.add('mobile-nav-open');$('#mobileNav').setAttribute('aria-expanded','true');$('#taskq').focus();requestAnimationFrame(()=>{let at=visible().findIndex(t=>t.id===cur),list=$('#tl');list.scrollTop=Math.max(0,at*navRow()-(list.clientHeight-navRow())/2);side()})}
$('#mobileNav').onclick=()=>document.body.classList.contains('mobile-nav-open')?closeMobileNav():openMobileNav();$('#drawerScrim').onclick=closeMobileNav;
function jumpToTask(n){let task=T.find(t=>t.n===Number(n));if(!task){toast('Enter a task number between 1 and '+T.length);return}F='all';q='';$('#taskq').value='';$$('.filter').forEach(b=>b.classList.toggle('on',b.dataset.f==='all'));reader(task.id);$('#reader').focus({preventScroll:true})}
$('#taskFilter').onchange=e=>{F=e.target.value;reader(cur,false)};
$('#jumpTask').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();jumpToTask(e.target.value)}};$('#latestTask').onclick=()=>jumpToTask(T.length);
$('#sessionSearchInput').onkeydown=e=>{if(e.key==='Escape'){closeSessionSearch();$('#searchSession').focus();return}if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(searchMatches.length){searchAt=(searchAt+(e.key==='ArrowDown'?1:-1)+searchMatches.length)%searchMatches.length;$$('.sresult').forEach((b,i)=>b.classList.toggle('active',i===searchAt));$(`.sresult[data-si="${searchAt}"]`)?.scrollIntoView({block:'nearest'})}}else if(e.key==='Enter'){e.preventDefault();if(searchMatches.length&&searchQuery===e.target.value.trim())gotoSearch(Math.max(0,searchAt));else runSessionSearch()}};
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeMobileNav();if($('#sessionSearchPanel').classList.contains('open'))closeSessionSearch()}});
// Trap tab focus only inside the active modal; return search focus on close.
document.addEventListener('keydown',e=>{if(e.key!=='Tab')return;let modal=$('#sessionSearchPanel.open')||$('#palette.open')||$('#helpmodal.open');if(!modal)return;let nodes=[...modal.querySelectorAll('input,select,button,[tabindex="0"]')].filter(n=>!n.disabled);if(!nodes.length)return;let first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}});

$('#refreshSession').onclick=()=>refreshManifest(true);$('#searchSession').onclick=openSessionSearch;refreshManifest();
