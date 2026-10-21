if('scrollRestoration' in history)history.scrollRestoration='manual';
const fileModel=JSON.parse(document.querySelector('#fileModel').textContent);
markdownSessionId=fileModel.sid||'';markdownTask=fileModel.task||'';
const fileEl=id=>document.getElementById(id);
let fileData=null,fileSource=false,fileController=null,fileGeneration=0,fileHeadings=[],fileOutlineOpen=false,fileSaveTimer=0;
function fileTheme(){document.documentElement.dataset.theme=localStorage.codexviewTheme||'light'}
function fileOutline(open){fileOutlineOpen=!!open&&!fileSource&&fileData?.kind==='markdown'&&fileHeadings.length>0;fileEl('fileOutline').hidden=!fileOutlineOpen;fileEl('fileLayout').classList.toggle('outline-open',fileOutlineOpen);fileEl('fileOutlineToggle').setAttribute('aria-expanded',String(fileOutlineOpen))}
function buildContents(){
 fileHeadings=[...fileEl('fileContent').querySelectorAll('h1[id],h2[id],h3[id],h4[id],h5[id],h6[id]')].slice(0,120);
 let nav=fileEl('fileOutlineLinks');nav.replaceChildren();
 for(let heading of fileHeadings){let a=document.createElement('a');a.href='#'+encodeURIComponent(heading.id);a.textContent=heading.textContent;a.dataset.depth=Math.min(3,Number(heading.tagName.slice(1)));a.onclick=()=>{if(innerWidth<=700)fileOutline(false)};nav.append(a)}
 fileEl('fileOutlineToggle').hidden=!fileHeadings.length;fileEl('fileOutlineToggle').textContent='Contents · '+fileHeadings.length;fileOutline(fileOutlineOpen);
}
function filePositionKey(){return 'codexviewFilePosition:'+fileData.path}
function saveFilePosition(){
 if(!fileData||fileData.kind!=='markdown'||fileSource)return;
 const body=fileEl('fileContent'),r=body.getBoundingClientRect();let target=document.elementFromPoint?.(Math.min(innerWidth-20,Math.max(20,r.left+r.width*.5)),Math.min(innerHeight-20,160));
 if(!body.contains(target))return;let block=target.closest('p,li,pre,h1,h2,h3,h4,h5,h6,table');if(!block)return;
 try{const key=filePositionKey();localStorage.setItem(key,JSON.stringify({v:1,size:fileData.size,modified:fileData.modified_ns,anchor:(block.textContent||'').slice(0,120),top:Math.round(block.getBoundingClientRect().top)}));let keys=JSON.parse(localStorage.getItem('codexviewFileRecent')||'[]');keys=Array.isArray(keys)?keys.filter(x=>typeof x==='string'&&x!==key):[];keys.unshift(key);for(let old of keys.slice(50))localStorage.removeItem(old);localStorage.setItem('codexviewFileRecent',JSON.stringify(keys.slice(0,50)))}catch{}
}
function restoreFilePosition(){
 if(location.hash){let id;try{id=decodeURIComponent(location.hash.slice(1))}catch{};if(id)document.getElementById(id)?.scrollIntoView({block:'start'});return}
 try{let saved=JSON.parse(localStorage.getItem(filePositionKey())||'null');if(saved?.v!==1||saved.size!==fileData.size||saved.modified!==fileData.modified_ns)return;for(let block of fileEl('fileContent').querySelectorAll('p,li,pre,h1,h2,h3,h4,h5,h6,table')){if(saved.anchor&&(block.textContent||'').startsWith(saved.anchor)){window.scrollBy({top:block.getBoundingClientRect().top-Math.max(-100000,Math.min(innerHeight,saved.top||0)),behavior:'instant'});break}}}catch{}
}
function displayFile(){
 if(!fileData)return;
 fileEl('fileRendered').setAttribute('aria-pressed',String(!fileSource));fileEl('fileSource').setAttribute('aria-pressed',String(fileSource));
 const frame=fileEl('fileFrame'),body=fileEl('fileContent');
 frame.classList.toggle('filehidden',fileSource||fileData.kind!=='html');body.classList.toggle('filehidden',!fileSource&&fileData.kind==='html');
 if(fileSource){fileOutline(false);fileEl('fileOutlineToggle').hidden=true;frame.removeAttribute('src');body.replaceChildren();const pre=document.createElement('pre');pre.textContent=fileData.text;body.append(pre)}
 else if(fileData.kind==='image'){fileOutline(false);fileEl('fileOutlineToggle').hidden=true;frame.removeAttribute('src');body.replaceChildren();let img=document.createElement('img');img.src=fileData.raw_url;img.alt=fileData.name;body.append(img)}
 else if(fileData.kind==='html'){fileOutline(false);fileEl('fileOutlineToggle').hidden=true;body.replaceChildren();let url=new URL(fileData.raw_url,location.href);if(fileModel.sid)url.searchParams.set('sid',fileModel.sid);if(fileModel.task)url.searchParams.set('task',fileModel.task);frame.src=url.pathname+url.search+location.hash}
 else{frame.removeAttribute('src');markdownFilePath=fileData.path;body.innerHTML=mdRender(fileData.text,{headings:true});buildContents();restoreFilePosition()}
}
async function readFile(){
 saveFilePosition();fileController?.abort();fileController=new AbortController();const generation=++fileGeneration;fileEl('fileMessage').textContent='Loading report…';
 try{
  const response=await fetch('/api/file?path='+encodeURIComponent(fileModel.path)+(fileModel.sid?'&sid='+encodeURIComponent(fileModel.sid):''),{signal:fileController.signal});const data=await response.json();if(generation!==fileGeneration)return;if(!response.ok)throw Error(data.error||'Unable to load report.');
  fileData=data;fileEl('fileSource').hidden=data.kind==='image';fileEl('fileImages').hidden=!(data.kind==='html'&&data.images?.length);fileEl('fileImages').textContent='Images · '+(data.images?.length||0);fileEl('fileImageLinks').hidden=true;document.title=data.name+' · CodexView';fileEl('fileName').textContent=data.name;
  let path=(data.relative_path||data.path).split('/').filter(Boolean);path.pop();fileEl('filePath').textContent=[data.root_name||'',...path.slice(-3)].filter(Boolean).join(' / ')||'Project reports';fileEl('filePath').title=data.path;
  fileEl('fileMessage').textContent=data.kind==='image'?'Image · Select the image to zoom. Saved files are read-only.':data.kind==='html'?'Static HTML · Local report links open in this reader. Scripts, forms and external resources stay disabled.':'Markdown · '+Intl.NumberFormat().format(data.size)+' bytes · Saved files are read-only.';displayFile();
 }catch(error){if(error.name!=='AbortError'&&generation===fileGeneration){fileEl('fileMessage').textContent=error.message;fileEl('fileContent').replaceChildren();let card=document.createElement('div');card.className='fileerror';card.textContent='Check that this report exists inside the project directory, then select Refresh.';fileEl('fileContent').append(card);fileEl('fileFrame').classList.add('filehidden');fileEl('fileFrame').removeAttribute('src');fileEl('fileContent').classList.remove('filehidden');fileEl('fileOutlineToggle').hidden=true;fileEl('fileImages').hidden=true;fileEl('fileImageLinks').hidden=true;fileOutline(false);fileData=null}}
}
if(fileModel.sid){fileEl('fileBack').href='/session/'+encodeURIComponent(fileModel.sid)+(fileModel.task?'?resume=1#task-'+fileModel.task:'?resume=1');fileEl('fileBack').textContent=fileModel.task?'← Task '+fileModel.task:'← Session'}
fileEl('fileRendered').onclick=()=>{fileSource=false;displayFile()};fileEl('fileSource').onclick=()=>{saveFilePosition();fileSource=true;displayFile()};fileEl('fileRefresh').onclick=readFile;
fileEl('fileOutlineToggle').onclick=()=>fileOutline(!fileOutlineOpen);
fileEl('fileCopyPath').onclick=async()=>{let path=fileData?.path||fileModel.path;try{await navigator.clipboard.writeText(path);fileEl('fileCopyPath').textContent='Copied';setTimeout(()=>fileEl('fileCopyPath').textContent='Copy path',1200)}catch{fileEl('fileMessage').textContent=path}};
fileEl('fileImages').onclick=()=>{let box=fileEl('fileImageLinks');box.hidden=!box.hidden;if(!box.hidden){box.replaceChildren();for(let url of fileData.images||[]){let u=new URL(url,location.href);u.searchParams.set('from',fileData.path);if(fileModel.task)u.searchParams.set('task',fileModel.task);let a=document.createElement('a');a.href=u.pathname+u.search;a.textContent=(u.searchParams.get('path')||'Image').split('/').pop();box.append(a)}}};
if(fileModel.from){let u=new URL('/file',location.href);u.searchParams.set('path',fileModel.from);if(fileModel.sid)u.searchParams.set('sid',fileModel.sid);if(fileModel.task)u.searchParams.set('task',fileModel.task);fileEl('fileBack').href=u.pathname+u.search;fileEl('fileBack').textContent='← Report'}
fileEl('fileTheme').onclick=()=>{localStorage.codexviewTheme=document.documentElement.dataset.theme==='dark'?'light':'dark';fileTheme()};
window.addEventListener('scroll',()=>{clearTimeout(fileSaveTimer);fileSaveTimer=setTimeout(saveFilePosition,650)},{passive:true});window.addEventListener('pagehide',saveFilePosition);document.addEventListener('visibilitychange',()=>{if(document.hidden)saveFilePosition()});
fileEl('fileName').textContent=fileModel.path.split('/').pop()||'Report';fileEl('filePath').title=fileModel.path;fileTheme();readFile();
