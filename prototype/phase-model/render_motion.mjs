// usage: node render_motion.mjs  (renders frames/ then encodes motion.mp4 and strip.jpg)
import {createRequire} from 'module';const require=createRequire(import.meta.url);
const {chromium}=require('playwright');import http from 'http';import fs from 'fs';import path from 'path';import {execSync} from 'child_process';
const root=path.dirname(new URL(import.meta.url).pathname);
const N=+process.env.N||150,FPS=N/5;
const srv=http.createServer((q,r)=>{let u=decodeURIComponent(q.url.split('?')[0]);let f=u.startsWith('/fonts/')?'/home/user/lumieralight'+u:path.join(root,u);
 try{const b=fs.readFileSync(f);r.writeHead(200,{'content-type':f.endsWith('.html')?'text/html':f.endsWith('.json')?'application/json':f.endsWith('.js')?'text/javascript':'application/octet-stream'});r.end(b)}catch(e){r.writeHead(404);r.end()}}).listen(0);
const port=srv.address().port;
fs.mkdirSync(path.join(root,'frames'),{recursive:true});
const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
p.on('pageerror',e=>console.log('ERR',e.message));
await p.addInitScript(`Object.assign(window,{D:'235',VO:'150',EL:'40'})`);
await p.goto(`http://localhost:${port}/scene_motion.html`);
await p.waitForFunction('window.DONE',null,{timeout:120000});await p.evaluate('document.fonts.ready');
const t0=Date.now();
for(let i=0;i<N;i++){await p.evaluate(`window.setFrame(${i})`);await p.screenshot({path:path.join(root,'frames',`f${String(i).padStart(4,'0')}.png`)});if(i==4)console.log('s/frame',(Date.now()-t0)/5000)}
await b.close();srv.close();
execSync(`ffmpeg -y -loglevel error -framerate ${FPS} -i frames/f%04d.png -c:v libx264 -crf 17 -pix_fmt yuv420p -movflags +faststart -an motion.mp4`,{cwd:root});
const idx=[0,1,2,3,4,5].map(i=>Math.round(i*(N-1)/5));
execSync(`ffmpeg -y -loglevel error ${idx.map(i=>`-i frames/f${String(i).padStart(4,'0')}.png`).join(' ')} -filter_complex "${idx.map((_,i)=>`[${i}:v]scale=360:-1[s${i}]`).join(';')};${idx.map((_,i)=>`[s${i}]`).join('')}hstack=6" -frames:v 1 -q:v 3 strip.jpg`,{cwd:root});
fs.rmSync(path.join(root,'frames'),{recursive:true});
