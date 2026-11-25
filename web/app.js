const $=id=>document.getElementById(id);
let library=[], selected=null, minutes=null, paper=null, side='cover', busy=false, lastNotice;
const saved=JSON.parse(sessionStorage.getItem('studioJob')||'null');
const conversation=JSON.parse(sessionStorage.getItem('studioConversation')||'[]');
let chatting=false, providers=[];
const backend=$('modelBackend');
function showModel(){
 const provider=providers.find(p=>p.id===backend.value);
 $('configure').hidden=!provider||provider.id==='codex';
 if(provider)$('modelLabel').textContent=[provider.model || (provider.id==='workbuddy'?'Harness default model':'Server configuration'),provider.vision?'Paper text and exhibit previews':'Paper text only'].join(' · ');
}
backend.onchange=()=>{sessionStorage.setItem('studioBackend',backend.value);showModel()};
const input=$('chatInput');
input.value=sessionStorage.getItem('studioDraft')||'';
function storeChat(){
 sessionStorage.setItem('studioConversation',JSON.stringify(conversation));
 sessionStorage.setItem('studioDraft',input.value);
}
function displayChat(){
 const log=$('chatLog');log.replaceChildren();
 for(const m of conversation){
  const row=document.createElement('div');row.className='message '+m.role;
  const who=document.createElement('b');who.textContent=m.role==='user'?'You':'Assistant';
  const content=document.createElement('p');content.textContent=m.content;
  row.append(who,content);log.append(row);
 }
 log.hidden=!conversation.length;log.scrollTop=log.scrollHeight;
 $('clearChat').hidden=!conversation.length&&!input.value;
}
function updateChat(){
 input.disabled=busy;backend.disabled=busy||chatting;$('configure').disabled=backend.disabled;
 $('chatSend').disabled=busy||chatting||!backend.value||!input.value.trim();
 $('clearChat').disabled=busy||chatting;
}
function addMessage(role,content,index=conversation.length){
 conversation.splice(index,0,{role,content});storeChat();displayChat();
}
input.oninput=()=>{storeChat();$('clearChat').hidden=!conversation.length&&!input.value;updateChat()};
input.onkeydown=e=>{
 if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){
  e.preventDefault();if(!$('chatSend').disabled)$('chatForm').requestSubmit();
 }
};
$('clearChat').onclick=()=>{
 conversation.length=0;input.value='';storeChat();displayChat();updateChat();
 $('chatStatus').textContent='Generate with these instructions, or send them to discuss first.';input.focus();
};
$('chatForm').onsubmit=async e=>{
 e.preventDefault();const request=input.value.trim();if(!request||busy||chatting)return;
 input.value='';addMessage('user',request);
 const replyIndex=conversation.length;chatting=true;updateChat();
 $('chatStatus').textContent='The assistant is replying…';
 try{
  const response=await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','X-Studio':'1'},
   body:JSON.stringify({messages:conversation,template:selected,minutes,backend:backend.value})});
  addMessage('assistant',response.reply,replyIndex);$('chatStatus').textContent='Add another instruction or generate your PowerPoint.';
 }catch(error){$('chatStatus').textContent=error.message+' You can generate now or send the message again.'}
 finally{chatting=false;updateChat()}
};
displayChat();updateChat();
function toast(message){$('notice').textContent=message;$('notice').hidden=false;clearTimeout(lastNotice);lastNotice=setTimeout(()=>$('notice').hidden=true,4500)}
async function api(url,options){const r=await fetch(url,options);const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed.');return d}
function showPage(isLibrary){$('desk').hidden=isLibrary;$('library').hidden=!isLibrary;$('deskNav').classList.toggle('active',!isLibrary);$('libraryNav').classList.toggle('active',isLibrary)}
$('deskNav').onclick=()=>showPage(false);$('libraryNav').onclick=()=>showPage(true);
function theme(){return library.find(t=>t.id===selected)||library[0]}
function box(el,b){['left','top','width','height'].forEach((k,i)=>el.style[k]=b[i]*100+'%')}
function preview(){
 const t=theme();if(!t)return;
 if(side==='closing'&&!t.closingTitle)side='cover';
 const baked=side==='closing'||(side==='cover'&&t.nativeBookends);
 $('closingTab').hidden=!t.closingTitle;
 $('sampleTitle').hidden=$('sampleSub').hidden=baked;
 const asset=side==='cover'&&t.nativeBookends?'cover-preview':side;
 $('bg').src='/library/'+t.id+'/'+asset+'.png';$('bg').alt=t.name+' template background';
 const isCover=side==='cover';const title=$('sampleTitle'),sub=$('sampleSub');
 const redBody=!isCover && t.id==='polyu-transcope';
 title.textContent=isCover?'Research Presentation':redBody?'Motivation':t.nativeBookends?'Motivation · Research question':'Research question';
 sub.textContent=isCover?'Authors & affiliations':'What question does the paper address?';
 box(title,isCover?t.cover:t.body);box(sub,isCover?t.subtitle:redBody?[.045,.115,.91,.10]:[.075,.33,.83,.15]);
 for(const el of [title,sub]){el.style.fontFamily=redBody?'Arial, sans-serif':'';el.style.fontWeight=redBody?'700':'';el.style.fontSize=redBody?'2.115cqw':''}
 title.style.justifyContent=sub.style.justifyContent=isCover?'center':'flex-start';
 function colors(){if(baked)return;const im=$('bg');if(!im.naturalWidth)return;const cn=document.createElement('canvas');cn.width=im.naturalWidth;cn.height=im.naturalHeight;const ctx=cn.getContext('2d');ctx.drawImage(im,0,0);for(const el of [title,sub]){
 const x=(parseFloat(el.style.left)+parseFloat(el.style.width)*.5)/100,y=(parseFloat(el.style.top)+parseFloat(el.style.height)*.5)/100;
 const rgb=ctx.getImageData(Math.min(cn.width-1,Math.max(0,x*cn.width)),Math.min(cn.height-1,Math.max(0,y*cn.height)),1,1).data;
 el.style.color=(rgb[0]*.3+rgb[1]*.59+rgb[2]*.11)<125?'white':'#172437'}}
 $('bg').onload=colors;if($('bg').complete)colors();
 $('themeName').textContent=t.name;const ratio=t.width/t.height;$('ratio').textContent=Math.abs(ratio-16/9)<.02?'16 ∶ 9':Math.abs(ratio-4/3)<.02?'4 ∶ 3':ratio.toFixed(2)+' ∶ 1';
 $('coverTab').setAttribute('aria-pressed',isCover);$('bodyTab').setAttribute('aria-pressed',side==='body');$('closingTab').setAttribute('aria-pressed',side==='closing')
}
$('coverTab').onclick=()=>{side='cover';preview()};$('bodyTab').onclick=()=>{side='body';preview()};
$('closingTab').onclick=()=>{side='closing';preview()};
function slides(m){const x=m*.8;return Math.min(30,Math.max(2,Math.round(x)+1))+(theme()?.closingTitle?1:0)}
function update(){
 $('styleText').textContent=selected?theme().name:'Choose template';$('timeText').textContent=minutes?minutes+' min':'Set duration';
 $('generate').disabled=busy||!backend.value||!paper||!selected||!minutes;
 $('generate').firstChild.textContent=busy?'Generating ': 'Generate PowerPoint ';
 $('planText').textContent=minutes?minutes+' min · '+slides(minutes)+(theme()?.closingTitle?' slides including cover and closing · ':' slides including cover · ')+(minutes<=7?'Main idea and key evidence':'Paper section order'):'Choose a template and speaking time to see your slide count.';
 updateChat();
 for(const id of ['drop','styleButton','timeButton'])$(id).disabled=busy
}
function tiles(id){const list=$(id);list.replaceChildren();for(const t of library){
 const btn=document.createElement('button');btn.className='tile'+(selected===t.id?' chosen':'');const img=new Image();img.src='/library/'+t.id+(t.nativeBookends?'/cover-preview.png':'/cover.png');img.alt='';
 const label=document.createElement('strong');label.textContent=t.name;const caption=document.createElement('small');caption.textContent=t.id===selected?'Selected':'Use this template →';btn.append(img,label,caption);
 btn.onclick=()=>{if(busy){toast('A presentation is being generated.');return}selected=t.id;side='cover';$('styles').close();showPage(false);refresh()};list.append(btn)
}}
function refresh(){tiles('shelf');tiles('choices');preview();update()}
async function load(){
 const data=await api('/api/templates');library=data.templates;providers=data.providers;
 const previous=backend.value||sessionStorage.getItem('studioBackend');
 backend.replaceChildren(...providers.map(p=>new Option(p.label,p.id)));
 backend.value=providers.some(p=>p.id===previous)?previous:data.backend;
 showModel();refresh();
}
$('styleButton').onclick=()=>$('styles').showModal();
$('timeButton').onclick=()=>{$('mins').value=minutes||'';estimate();$('timing').showModal()};
document.querySelectorAll('.close').forEach(b=>b.onclick=()=>b.closest('dialog').close());
const validTime=()=>Number.isInteger(+$('mins').value)&&+$('mins').value>=1&&+$('mins').value<=45;
function estimate(){$('confirmTime').disabled=!validTime();$('estimate').textContent=validTime()?'Estimated: '+slides(+$('mins').value)+(theme()?.closingTitle?' slides, including cover and closing.':' slides, including the cover.'):'Enter a duration from 1 to 45 minutes.'}
for(const m of [3,5,10,15,20]){const b=document.createElement('button');b.textContent=m+' min';b.onclick=()=>{$('mins').value=m;estimate()};$('presets').append(b)}
$('mins').oninput=estimate;$('confirmTime').onclick=()=>{if(validTime()){minutes=+$('mins').value;$('timing').close();update()}};
function selectPaper(f){if(!f)return;if(!/\.pdf$/i.test(f.name)||f.size>45*1024*1024){toast('Choose a PDF of 45 MB or less');return}paper=f;$('fileTitle').textContent=f.name;$('fileInfo').textContent=(f.size/1024/1024).toFixed(1)+' MB · Click to replace';update()}
$('drop').onclick=()=>$('pdf').click();$('pdf').onchange=()=>selectPaper($('pdf').files[0]);
for(const ev of ['dragover','dragleave','drop'])$('drop').addEventListener(ev,e=>{e.preventDefault();$('drop').classList.toggle('over',ev==='dragover');if(ev==='drop'&&!busy)selectPaper(e.dataTransfer.files[0])});
function openImport(){$('styles').close();$('importState').textContent='';$('importDialog').showModal()}
for(const id of ['importLibrary','importChoice','addLink'])$(id).onclick=openImport;
$('ppt').onchange=()=>{const f=$('ppt').files[0];if(f)$('importName').value=f.name.replace(/\.pptx$/i,'')};
$('importSubmit').onclick=async()=>{
 const f=$('ppt').files[0];if(!f||!f.name.toLowerCase().endsWith('.pptx')||f.size>45*1024*1024){$('importState').textContent='Choose a .pptx file of 45 MB or less.';return}
 $('importSubmit').disabled=true;$('importState').textContent='Extracting cover and content layouts…';
 try{const t=await api('/api/templates?name='+encodeURIComponent($('importName').value||f.name.replace(/\.pptx$/i,'')),{method:'POST',headers:{'X-Studio':'1'},body:f});
 if(!busy)selected=t.id;await load();$('importDialog').close();toast('Template added to the library.');$('ppt').value='';$('importName').value=''}
 catch(e){$('importState').textContent=e.message}finally{$('importSubmit').disabled=false}
};
function statePanel(){const p=$('result');p.hidden=false;$('download').hidden=true;$('outline').replaceChildren();$('resultTitle').textContent='Generation progress';$('fill').style.width='5%';$('progress').textContent='Uploading your paper…';$('elapsed').textContent='';}
async function follow(id,start){
 busy=true;update();let failedPolls=0;
 while(true){
 let d;
 try{d=await api('/api/jobs/'+id);failedPolls=0}catch(e){if(++failedPolls>=4)throw e;await new Promise(r=>setTimeout(r,1500));continue}
 $('elapsed').textContent=Math.max(0,Math.floor((Date.now()-start)/1000))+' s';$('progress').textContent=d.message;$('fill').style.width=([6,23,53,84,100][d.step]||0)+'%';
 if(d.status==='done'){sessionStorage.removeItem('studioJob');$('resultTitle').textContent=d.title;$('progress').textContent=d.theme+' · '+d.minutes+' min · '+d.pages+' slides';for(const name of d.outline){const li=document.createElement('li');li.textContent=name;$('outline').append(li)}$('download').href='/api/jobs/'+id+'/download';$('download').hidden=false;break}
 if(d.status==='error'){sessionStorage.removeItem('studioJob');$('resultTitle').textContent='Generation failed';break}
 await new Promise(r=>setTimeout(r,1500))
 }
}
$('generate').onclick=async()=>{
 if(busy||!paper||!minutes||!selected)return;busy=true;update();statePanel();$('result').scrollIntoView({behavior:'smooth',block:'nearest'});
 try{
 const draft=input.value.trim();
 if(draft){input.value='';addMessage('user',draft)}
 const body=new FormData();body.append('paper',paper);body.append('conversation',JSON.stringify(conversation));
 const start=Date.now();const {id}=await api('/api/jobs?'+new URLSearchParams({minutes,template:selected,backend:backend.value}),{method:'POST',headers:{'X-Studio':'1'},body});sessionStorage.setItem('studioJob',JSON.stringify({id,start}));await follow(id,start)}
 catch(e){$('progress').textContent=e.message;$('resultTitle').textContent='Connection failed'}finally{busy=false;update()}
};
load().then(async()=>{if(saved){statePanel();try{await follow(saved.id,saved.start)}catch(e){$('progress').textContent=e.message}finally{busy=false;update()}}}).catch(e=>toast(e.message));

const connectionDialog=$('connectionDialog');
const form=$('connectionForm');
const portals={
 internal:'https://copilot.tencent.com/profile/',
 international:'https://www.codebuddy.ai/profile/keys',
 ioa:'https://tencent.sso.copilot.tencent.com/profile/keys',
 inherit:'https://www.codebuddy.cn/docs/cli/iam'
};
let editingProvider, submitting=false;

function updateKeyHelp(){
 const p=editingProvider;
 const changed=p.id==='openai-compatible'&&$('connectionBase').value.trim().replace(/\/+$/,'')!==p.base
     ||p.id==='workbuddy'&&$('connectionRegion').value!==p.region;
 const reuse=p.hasKey&&!changed;
 $('connectionKey').placeholder=reuse?'Leave blank to keep the current key':'Enter your API key';
 $('connectionKey').required=p.id==='deepseek'&&!reuse;
 $('keyHelp').textContent=p.id==='workbuddy'?'Use a CodeBuddy key for the selected edition, or leave blank to use an existing harness login.'
     :p.id==='openai-compatible'?'Optional for local servers. Enter a new key when changing the endpoint.':'Use a key from your DeepSeek account.';
 const link=$('keyPortal');
 link.hidden=p.id==='openai-compatible';
 link.href=p.id==='deepseek'?'https://platform.deepseek.com/api_keys':portals[$('connectionRegion').value];
}
function fillConnection(p){
 editingProvider=p;
 $('connectionTitle').textContent=p.label+' settings';
 $('regionField').hidden=p.id!=='workbuddy';
 $('baseField').hidden=p.id!=='openai-compatible';
 $('connectionBase').required=!$('baseField').hidden;
 $('connectionBase').value=p.base;
 $('connectionModel').value=p.model;
 $('connectionModel').required=p.id==='openai-compatible';
 $('connectionModel').placeholder=p.id==='workbuddy'?'Use the harness default':p.id==='deepseek'?'deepseek-flash':'Model served by the endpoint';
 $('connectionRegion').value=p.region;
 $('visionField').hidden=p.id==='workbuddy';
 $('connectionVision').checked=p.vision;
 $('connectionKey').value='';
 $('rememberConnection').checked=p.remembered;
 $('resetConnection').hidden=!p.customized;
 updateKeyHelp();
}
$('configure').onclick=()=>{
 fillConnection(providers.find(p=>p.id===backend.value));
 $('connectionStatus').textContent='';connectionDialog.showModal();
};
$('connectionRegion').onchange=updateKeyHelp;
$('connectionBase').oninput=updateKeyHelp;
connectionDialog.onclose=()=>{$('connectionKey').value=''};
connectionDialog.oncancel=e=>{if(submitting)e.preventDefault()};
async function submitConnection(action){
 if(submitting)return;
 const p=editingProvider;
 const values={model:$('connectionModel').value,base:$('connectionBase').value,key:$('connectionKey').value,
   region:$('connectionRegion').value,vision:$('connectionVision').checked,remember:$('rememberConnection').checked};
 submitting=true;
 const controls=[...connectionDialog.querySelectorAll('input, select, button')];
 controls.forEach(el=>el.disabled=true);
 const status=$('connectionStatus');
 status.textContent=action==='test'?'Sending a short test message…':'Updating settings…';
 try{
  const response=await api('/api/providers/'+p.id+'/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-Studio':'1'},
    body:JSON.stringify(action==='reset'?{}:values)});
  if(action==='test'){status.textContent=response.message;return}
  providers=providers.map(item=>item.id===p.id?response:item);showModel();
  connectionDialog.close();
  toast(action==='reset'?'Settings cleared. Using startup defaults.':'Settings saved. Ready to use.');
 }catch(error){status.textContent=error.message}
 finally{submitting=false;controls.forEach(el=>el.disabled=false)}
}
form.onsubmit=e=>{e.preventDefault();submitConnection(e.submitter?.value||'save')};
$('resetConnection').onclick=()=>submitConnection('reset');
