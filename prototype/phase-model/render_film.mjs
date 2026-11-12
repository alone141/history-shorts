// usage: node render_film.mjs [workers]   renders frames_film/ in parallel workers, then encodes picture_silent.mp4 and film_strip source frames.
// internal: node render_film.mjs --worker start end   (also: --probe f1,f2,... prints checks and writes probe_<f>.png)
import {createRequire} from 'module';const require=createRequire(import.meta.url);
const {chromium}=require('playwright');import http from 'http';import fs from 'fs';import path from 'path';import {execSync,spawn} from 'child_process';
const root=path.dirname(new URL(import.meta.url).pathname);
const NAR=JSON.parse(fs.readFileSync(path.join(root,'narration.json')));const N=NAR.frames;
const a=process.argv.slice(2);
async function work(list,tag){
 const srv=http.createServer((q,r)=>{let u=decodeURIComponent(q.url.split('?')[0]);let f=u.startsWith('/fonts/')?'/home/user/lumieralight'+u:path.join(root,u);
  try{const b=fs.readFileSync(f);r.writeHead(200,{'content-type':f.endsWith('.html')?'text/html':f.endsWith('.json')?'application/json':f.endsWith('.js')?'text/javascript':'application/octet-stream'});r.end(b)}catch(e){r.writeHead(404);r.end()}}).listen(0);
 const port=srv.address().port;fs.mkdirSync(path.join(root,'frames_film'),{recursive:true});
 const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const p=await b.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
 p.on('pageerror',e=>console.log('ERR',e.message));
 await p.addInitScript(`Object.assign(window,{D:'235',VO:'150',EL:'40'})`);
 await p.goto(`http://localhost:${port}/scene_film.html`);
 await p.waitForFunction('window.DONE',null,{timeout:180000});await p.evaluate('document.fonts.ready');
 const t0=Date.now();let k=0;
 for(const i of list){await p.evaluate(`window.setFrame(${i})`);
  if(tag==='probe'){const info=await p.evaluate(`(()=>{const c=document.getElementById('cap');return {lines:Math.round(c.getBoundingClientRect().height/49),bottom:c.getBoundingClientRect().bottom,right:c.getBoundingClientRect().right,stats:window.STATS,tl:window.TL}})()`);console.log(i,JSON.stringify(info));
   await p.screenshot({path:path.join(root,`probe_${i}.png`)});}
  else await p.screenshot({path:path.join(root,'frames_film',`f${String(i).padStart(4,'0')}.png`)});
  if(++k%20==0)console.log(tag,k,'/',list.length,((Date.now()-t0)/k/1000).toFixed(2),'s/frame',flush())}
 await b.close();srv.close()}
function flush(){return ''}
if(a[0]==='--worker'){const s=+a[1],e=+a[2];await work(Array.from({length:e-s},(_,i)=>s+i),'w'+s)}
else if(a[0]==='--probe'){await work(a[1].split(',').map(Number),'probe')}
else{
 const W=+a[0]||4;const per=Math.ceil(N/W);const ps=[];
 for(let w=0;w<W;w++){const s=w*per,e=Math.min(N,s+per);if(s>=e)continue;
  ps.push(new Promise(res=>{const c=spawn('node',[path.join(root,'render_film.mjs'),'--worker',s,e],{stdio:'inherit'});c.on('exit',res)}))}
 await Promise.all(ps);
 const miss=[];for(let i=0;i<N;i++)if(!fs.existsSync(path.join(root,'frames_film',`f${String(i).padStart(4,'0')}.png`)))miss.push(i);
 if(miss.length){console.log('MISSING',miss.length);process.exit(1)}
 execSync(`ffmpeg -y -loglevel error -framerate 30 -i frames_film/f%04d.png -c:v libx264 -crf 17 -pix_fmt yuv420p -movflags +faststart -an picture_silent.mp4`,{cwd:root});
 const idx=Array.from({length:8},(_,i)=>Math.round((i+0.5)*(N-1)/8));
 execSync(`ffmpeg -y -loglevel error ${idx.map(i=>`-i frames_film/f${String(i).padStart(4,'0')}.png`).join(' ')} -filter_complex "${idx.map((_,i)=>`[${i}:v]scale=270:-1[s${i}]`).join(';')};${idx.map((_,i)=>`[s${i}]`).join('')}hstack=8" -frames:v 1 -q:v 3 film_strip.jpg`,{cwd:root});
 fs.rmSync(path.join(root,'frames_film'),{recursive:true});console.log('encoded')}
