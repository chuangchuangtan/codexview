// Retain geometry when old tasks leave the DOM. Scroll adoption never seeks.
const taskHeights=new Map();
function readerTop(){return Math.max(90,($('#readingContext')?.getBoundingClientRect().bottom||78)+12)}
function viewAnchor(){
 const r=$('#reader')?.getBoundingClientRect();let node=r&&document.elementFromPoint?.(Math.max(12,Math.min(innerWidth-12,r.left+r.width*.45)),readerTop());
 node=node?.closest?.('.sec,.taskhead,h2,.task')||$(`.task[data-id="${CSS.escape(cur||'')}"]`);
 return node?{node,top:node.getBoundingClientRect().top}:null;
}
function keepView(anchor){if(!anchor?.node.isConnected)return;let delta=anchor.node.getBoundingClientRect().top-anchor.top;if(Math.abs(delta)>.5)window.scrollBy({top:delta,behavior:'instant'})}
function taskExtent(node){let s=getComputedStyle(node);return node.getBoundingClientRect().height+(parseFloat(s.marginTop)||0)+(parseFloat(s.marginBottom)||0)}
function taskSpacers(){let root=$('#reader');for(let id of ['readerBefore','readerAfter'])if(!$('#'+id)){let n=document.createElement('div');n.id=id;n.className='reader-spacer';n.setAttribute('aria-hidden','true');id==='readerBefore'?root.prepend(n):root.append(n)}}
function updateTaskSpacers(W){
 if(!W.length)return;let valid=new Set(visible().map(t=>t.id)),before=0,after=0;
 for(let [id,data] of taskHeights)if(valid.has(id)){if(data.n<W[0].n)before+=data.height;else if(data.n>W[W.length-1].n)after+=data.height}
 taskSpacers();$('#readerBefore').style.height=before+'px';$('#readerAfter').style.height=after+'px';
}
function trimTaskWindow(W,reset=false){
 let anchor=viewAnchor(),keep=new Set(W.map(t=>t.id));if(reset)taskHeights.clear();
 for(let node of [...$('#reader').children]){
  if(node.classList.contains('reader-spacer'))continue;
  if(!node.classList.contains('task')){node.remove();continue}
  if(!keep.has(node.dataset.id)){let t=T.find(t=>t.id===node.dataset.id);if(t&&!reset)taskHeights.set(t.id,{n:t.n,height:taskExtent(node)});node.querySelectorAll('.section-chunk').forEach(n=>chunkObserver.unobserve(n));node.remove()}
 }
 updateTaskSpacers(W);keepView(anchor);
}
function insertTask(node,t,W){
 let anchor=viewAnchor();taskSpacers();let later=[...$('#reader').querySelectorAll(':scope > .task')].find(n=>(T.find(x=>x.id===n.dataset.id)?.n||0)>t.n);
 $('#reader').insertBefore(node,later||$('#readerAfter'));updateTaskSpacers(W);keepView(anchor);
}
// Exceptional tasks use small section chunks, with exact heights retained on eviction.
const CHUNK_SIZE=24,CHUNK_LIMIT=5;
function chunkMarkup(sections,lazy=false){let out=[],activity=[];function flush(){if(activity.length){out.push(`<details class="ag" data-first="${activity[0].i}" data-last="${activity[activity.length-1].i}" data-total="${activity.length}"><summary><span class="ag-icon">⌁</span><span class="ag-label">${activity.length} activity steps</span><span class="ag-stats"></span></summary><div class="ab">${lazy?'':activity.map(sh).join('')}</div></details>`);activity=[]}}
 for(let s of sections){if(s.role==='Activity')activity.push(s);else{flush();out.push(sh(s))}}flush();return out.join('')}
function sectionMarkup(t){if(t.sections.length<=72)return chunkMarkup(t.sections);let out=[];for(let i=0;i<t.sections.length;i+=CHUNK_SIZE){let slice=t.sections.slice(i,i+CHUNK_SIZE),h=slice.reduce((n,s)=>n+(s.role==='User'||s.role==='Assistant'?220:12),0);out.push(`<div class="section-chunk" data-begin="${i}" data-end="${i+slice.length}" style="height:${Math.max(80,h)}px"></div>`)}return out.join('')}
function mountChunk(slot){if(!slot||!slot.isConnected||slot.dataset.mounted)return;let t=T.find(x=>x.id===slot.closest('.task')?.dataset.id);if(!t)return;let anchor=viewAnchor();slot.style.height='';slot.innerHTML=chunkMarkup(t.sections.slice(+slot.dataset.begin,+slot.dataset.end),true);slot.dataset.mounted='1';keepView(anchor)}
function ensureSection(task,i){let slot=[...task.querySelectorAll('.section-chunk')].find(n=>i>=+n.dataset.begin&&i<+n.dataset.end);mountChunk(slot);let group=[...task.querySelectorAll('.ag[data-first]')].find(n=>i>=+n.dataset.first&&i<=+n.dataset.last);if(group)mountActivity(group);return task.querySelector(`.sec[data-i="${i}"],.aitem[data-i="${i}"]`)}
const chunkObserver=new IntersectionObserver(entries=>{for(let e of entries)if(e.isIntersecting){mountChunk(e.target);hydrate(e.target,token);trimChunks(e.target.closest('.task'))}},{rootMargin:'900px'});
function observeChunks(task){task.querySelectorAll('.section-chunk').forEach(n=>chunkObserver.observe(n));if(task.querySelector('.section-chunk')&&!task.querySelector('.sec'))mountChunk(task.querySelector('.section-chunk'))}
function trimChunks(task){if(!task)return;let mounted=[...task.querySelectorAll('.section-chunk[data-mounted]')];if(mounted.length<=CHUNK_LIMIT)return;
 let ranked=mounted.map(n=>({n,r:n.getBoundingClientRect()})).sort((a,b)=>Math.abs((a.r.top+a.r.bottom)/2-innerHeight/2)-Math.abs((b.r.top+b.r.bottom)/2-innerHeight/2));
 for(let {n,r} of ranked.slice(CHUNK_LIMIT)){if(r.bottom>-900&&r.top<innerHeight+900||n.contains(document.activeElement)||n.querySelector('.exact-search-hit'))continue;let anchor=viewAnchor();n.style.height=r.height+'px';n.replaceChildren();delete n.dataset.mounted;keepView(anchor)}
}

function mountActivity(group){let box=group.querySelector('.ab');if(box.children.length)return;let t=T.find(t=>t.id===group.closest('.task')?.dataset.id);if(t)box.innerHTML=t.sections.filter(s=>s.i>=+group.dataset.first&&s.i<=+group.dataset.last&&s.role==='Activity').map(sh).join('')}
document.addEventListener('toggle',e=>{if(e.target.matches('.ag[data-first]')&&e.target.open)mountActivity(e.target)},true);

async function ensureTaskMetadata(t,tok){if(t.loaded)return;let ctl=new AbortController();ctrls.push(ctl);let r=await fetch(`/api/session/${encodeURIComponent(M.sid)}/task/${t.id}`,{signal:ctl.signal}),d=await r.json();if(!r.ok)throw Error(d.error||'Task load failed');if(tok!==token)throw new DOMException('Navigation superseded','AbortError');t.sections=d.sections;t.started_at=d.started_at;t.loaded=true}
function newTaskNode(t){let box=document.createElement('div');box.innerHTML=th(t);return box.firstElementChild}
let edgeBusy=false;
async function preloadTaskEdge(dir){
 if(edgeBusy||readerBusy||layoutDragging)return;let nodes=[...$('#reader').querySelectorAll(':scope > .task')];if(nodes.length<2)return;
 let first=nodes[0],last=nodes[nodes.length-1],V=visible(),edge=dir>0?last:first,at=V.findIndex(t=>t.id===edge.dataset.id),t=V[at+dir];if(!t)return;
 if(dir>0&&(first.getBoundingClientRect().bottom>readerTop()-40||last.getBoundingClientRect().top>innerHeight+900))return;
 if(dir<0&&(last.getBoundingClientRect().top<innerHeight+40||first.getBoundingClientRect().bottom<-900))return;
 edgeBusy=true;let tok=token;
 try{await ensureTaskMetadata(t,tok);if(tok!==token||readerBusy)return;let W=dir>0?[...nodes.slice(1).map(n=>T.find(t=>t.id===n.dataset.id)),t]:[t,...nodes.slice(0,-1).map(n=>T.find(t=>t.id===n.dataset.id))];trimTaskWindow(W);let n=newTaskNode(t);n.style.minHeight=Math.min(720,innerHeight)+'px';insertTask(n,t,W);observeChunks(n);await hydrate(n,tok);if(n.isConnected){let anchor=viewAnchor();n.style.minHeight='';keepView(anchor)}observeProse()}
 catch(e){if(e.name!=='AbortError')console.debug('Adjacent task will retry when visible')}
 finally{edgeBusy=false;checkUserBoundary()}
}
