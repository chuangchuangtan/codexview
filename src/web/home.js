'use strict';
let D=[],source='all',busy=false;
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function themeHome(){document.documentElement.dataset.theme=localStorage.codexviewTheme||'dark'}
themeHome();
$('#themeHome').onclick=()=>{localStorage.codexviewTheme=document.documentElement.dataset.theme==='dark'?'light':'dark';themeHome()};
function size(n){return n>=1073741824?(n/1073741824).toFixed(1)+' GB':n>=1048576?(n/1048576).toFixed(1)+' MB':Math.ceil(n/1024)+' KB'}
function draw(){
 let q=$('#q').value.trim().toLowerCase(),a=D.filter(x=>(source==='all'||x.adapter===source)&&(x.id+' '+x.file+' '+(x.title||'')).toLowerCase().includes(q));
 a.sort($('#sort').value==='size'?(a,b)=>b.size-a.size:$('#sort').value==='title'?(a,b)=>(a.title||a.file).localeCompare(b.title||b.file):(a,b)=>b.mtime_ns-a.mtime_ns);
 $('#stats').textContent=a.length+' sessions';$('#librarySize').textContent=size(D.reduce((n,x)=>n+x.size,0))+' on disk';
 $('#list').innerHTML=a.map(x=>`<a class="session-card" href="/session/${encodeURIComponent(x.id)}"><div class="session-icon">${x.adapter==='native-jsonl'?'⌘':'≡'}</div><div class="session-body"><div class="session-card-top"><span class="source-label">${x.adapter==='native-jsonl'?'NATIVE CODEX':'MARKDOWN'}</span><span>${esc(x.updated?.slice(0,16)||'')}</span></div><h2 class="session-title">${esc(x.title||x.file)}</h2><div class="session-meta"><span>${size(x.size)}</span><span>${x.tasks==null?'Tasks on demand':x.tasks+' tasks'}</span>${x.reviewed?`<span class="rev">✓ ${x.reviewed} reviewed</span>`:''}${x.important?`<span class="imp">★ ${x.important}</span>`:''}</div><div class="session-id">${esc(x.id)}</div></div><span class="session-open" aria-hidden="true">↗</span></a>`).join('')||`<div class="home-empty"><b>${D.length?'No sessions match your filters':'No sessions found yet'}</b><p>${D.length?'Try a shorter title or another source.':'Start a Codex CLI conversation, then refresh. CodexView discovers sessions in CODEX_HOME/sessions.'}</p></div>`;
}
async function load(force=false){if(busy)return;busy=true;$('#refresh').disabled=true;$('#homeStatus').textContent='';try{let r=await fetch('/api/sessions'+(force?'?refresh=1':''));if(!r.ok)throw Error('Server returned '+r.status);D=await r.json();draw()}catch(e){$('#homeStatus').textContent='Could not load sessions. Check the connection and refresh.'}finally{busy=false;$('#refresh').disabled=false}}
$('#q').oninput=draw;$('#sort').onchange=draw;$('#refresh').onclick=()=>load(true);
document.querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>{source=b.dataset.source;document.querySelectorAll('[data-source]').forEach(n=>{n.classList.toggle('on',n===b);n.setAttribute('aria-pressed',n===b)});draw()});
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('#q').focus()}if(e.key==='Escape'){$('#q').value='';draw()}});
load();setInterval(()=>{if(!document.hidden)load()},60000);
