const fileModel=JSON.parse(document.querySelector('#fileModel').textContent);
markdownSessionId=fileModel.sid||'';
const fileEl=id=>document.getElementById(id);
let fileData=null,fileSource=false,fileController=null,fileGeneration=0;
function fileTheme(){document.documentElement.dataset.theme=localStorage.codexviewTheme||'light'}
function displayFile(){
  if(!fileData)return;
  fileEl('fileRendered').setAttribute('aria-pressed',String(!fileSource));
  fileEl('fileSource').setAttribute('aria-pressed',String(fileSource));
  const frame=fileEl('fileFrame'),body=fileEl('fileContent');
  frame.classList.toggle('filehidden',fileSource||fileData.kind!=='html');
  body.classList.toggle('filehidden',!fileSource&&fileData.kind==='html');
  if(fileSource){frame.removeAttribute('src');body.replaceChildren();const pre=document.createElement('pre');pre.textContent=fileData.text;body.append(pre)}
  else if(fileData.kind==='html'){body.replaceChildren();frame.src=fileData.raw_url}
  else{frame.removeAttribute('src');markdownFilePath=fileData.path;body.innerHTML=mdRender(fileData.text);if(location.hash){let id;try{id=decodeURIComponent(location.hash.slice(1))}catch{};if(id)document.getElementById(id)?.scrollIntoView()}}
}
async function readFile(){
  fileController?.abort();fileController=new AbortController();const generation=++fileGeneration;
  fileEl('fileMessage').textContent='Loading report…';
  try{
    const response=await fetch('/api/file?path='+encodeURIComponent(fileModel.path)+(fileModel.sid?'&sid='+encodeURIComponent(fileModel.sid):''),{signal:fileController.signal});
    const data=await response.json();if(generation!==fileGeneration)return;if(!response.ok)throw Error(data.error||'Unable to load report.');
    fileData=data;document.title=data.name+' · CodexView';fileEl('filePath').textContent=data.path;
    fileEl('fileMessage').textContent=data.kind==='html'?'Read-only static HTML · Scripts, forms and external resources are disabled. Relative local images and CSS are supported.':'Read-only Markdown · '+Intl.NumberFormat().format(data.size)+' bytes · Refresh to read saved changes.';
    displayFile();
  }catch(error){if(error.name!=='AbortError'){fileEl('fileMessage').textContent=error.message;fileEl('fileContent').textContent='Check the server path and configured --file-root, then select Refresh.';fileEl('fileFrame').classList.add('filehidden');fileEl('fileFrame').removeAttribute('src');fileEl('fileContent').classList.remove('filehidden');fileData=null}}
}
if(fileModel.sid){fileEl('fileBack').href='/session/'+encodeURIComponent(fileModel.sid);fileEl('fileBack').textContent='← Session'}
fileEl('fileRendered').onclick=()=>{fileSource=false;displayFile()};
fileEl('fileSource').onclick=()=>{fileSource=true;displayFile()};
fileEl('fileRefresh').onclick=readFile;
fileEl('fileTheme').onclick=()=>{localStorage.codexviewTheme=document.documentElement.dataset.theme==='dark'?'light':'dark';fileTheme()};
fileEl('filePath').textContent=fileModel.path;fileTheme();readFile();
