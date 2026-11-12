# Full narrated test film (picture only -> film_silent.mp4 + film_strip.jpg). Every value is a pure function of the frame number.
# Timeline comes from narration.json (the narration is the clock). Rebuild: see NOTES.md (build_film.sh).
import numpy as np, math, subprocess, os, re, json
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter
Image.MAX_IMAGE_PIXELS=None
src=open('build.py').read()
A=re.search(r"^A='(.*)'",src,re.M).group(1); F='/home/user/lumieralight/fonts/'
W,H=1080,1920; FPS=30
SIG=(240,68,28); INK=(21,23,26)
NAR=json.load(open('narration.json'))
S=[(o['start_s'],o['end_s']) for o in NAR]
DUR=28.8; NF=int(round(DUR*FPS))
rng=np.random.default_rng(3)
def font(n,s): return ImageFont.truetype(F+n,s)
# ---- static scene (as build.py / render_motion.py)
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
d=np.sqrt(((xx-W/2)/(W*0.75))**2+((yy-900)/(H*0.6))**2); g=0.975-0.16*d**2
tab=np.stack([g*0.962,g*0.978,g*1.0],-1)*255; tab+=rng.normal(0,1.6,(H,W,1))
bg=Image.fromarray(np.clip(tab,0,255).astype('uint8')).convert('RGBA')
dr=ImageDraw.Draw(bg); dr.rectangle([0,0,W,H],outline=(38,41,46),width=14); dr.rectangle([14,14,W-14,H-14],outline=(168,174,182),width=4)
def plate(i,w,rot):
    im=Image.open(A+f'jp2/b30448554_{i:04d}.jp2').convert('RGB'); s=w/im.width
    t=im.resize((w,round(im.height*s)),Image.LANCZOS).convert('RGBA')
    a=np.asarray(t).astype(np.float32); a[...,:3]=np.clip(a[...,:3]*1.06+6,0,255)
    return im,s,Image.fromarray(a.astype('uint8')).rotate(rot,expand=True,resample=Image.BICUBIC)
def paste(base,r,x,y):
    al=r.split()[3]
    sh=Image.new('RGBA',base.size,(0,0,0,0)); m=Image.new('L',base.size,0); m.paste(al,(x+10,y+16))
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(14)).point(lambda v:int(v*0.34))); base.alpha_composite(sh)
    m2=Image.new('L',base.size,0); m2.paste(al,(x+2,y+3)); s2=Image.new('RGBA',base.size,(0,0,0,0)); s2.putalpha(m2.filter(ImageFilter.GaussianBlur(3)).point(lambda v:int(v*0.3))); base.alpha_composite(s2)
    base.alpha_composite(r,(x,y))
im59,s59,r59=plate(59,500,-4); paste(bg,r59,40,310)
_,_,r=plate(83,560,3.5); paste(bg,r,500,325)
PW=980; PX=10; PY=722
im67,s67,r=plate(67,PW,0); paste(bg,r,PX,PY)
MAG=2.5; R=230
# lens target 1: lintel (as the 5 s clip)
bx,by=900,230; cxm=bx/1400*7603; cym=by/734*3985
L1=np.array([float(round(PX+cxm*s67)),float(round(PY+cym*s67))])
lx=(898-bx)*PW/1400*MAG; ly=(170-by)*PW/1400*MAG
ax,ay=140*PW/1400*MAG/2+14, 55*PW/1400*MAG/2+14
# lens target 2: man with staff + dog at the foot of the stones (scan px from 4x preview bbox 297-478 x 630-845)
gx=PX+(297+478)/2*4*s67; gy=PY+(630+845)/2*4*s67
L2=np.array([245.,1100.])
mx2=(gx-L2[0])*MAG; my2=(gy-L2[1])*MAG; ax2=(478-297)/2*4*s67*MAG+16; ay2=(845-630)/2*4*s67*MAG+14
# plan plate ring: corners of rotated plate 59
w0,h0=500,round(im59.height*500/im59.width); th=math.radians(-4); c_,s_=math.cos(th),math.sin(th)
Wp,Hp=r59.size; pcx,pcy=40+Wp/2,310+Hp/2; MG=14
def corner(du,dv): return (pcx+du*c_+dv*s_, pcy-du*s_+dv*c_)
RING=[corner(-w0/2-MG,-h0/2-MG),corner(w0/2+MG,-h0/2-MG),corner(w0/2+MG,h0/2+MG),corner(-w0/2-MG,h0/2+MG)]; RING.append(RING[0])
# masters at 2.5x the table scale, levelled once
def master_of(im,w):
    MW=round(w*MAG); m=im.resize((MW,round(im.height*MW/im.width)),Image.LANCZOS)
    return Image.fromarray(np.clip((np.asarray(m).astype(np.float32)-70)*1.18+14,0,255).astype('uint8'))
master=master_of(im67,PW)
y2,x2=np.mgrid[0:2*R,0:2*R].astype(np.float32); rr=np.hypot(x2-R,y2-R)/R; lensvig=(1-0.10*rr**3)[...,None]
ss=3
mask=Image.new('L',(2*R*ss,2*R*ss),0); ImageDraw.Draw(mask).ellipse([0,0,2*R*ss-1,2*R*ss-1],fill=255); mask=mask.resize((2*R,2*R),Image.LANCZOS)
M=R+110; SZ=2*M
sm=Image.new('L',(SZ,SZ),0); sm.paste(mask,(M-R+16,M-R+26)); sm=sm.filter(ImageFilter.GaussianBlur(22)).point(lambda v:int(v*0.45))
under=Image.new('RGBA',(SZ,SZ),(0,0,0,0)); under.putalpha(sm)
ring=Image.new('RGBA',(SZ,SZ),(0,0,0,0)); rd=ImageDraw.Draw(ring)
rd.ellipse([M-R-34,M-R-34,M+R+34,M+R+34],fill=(235,242,248,120)); rd.ellipse([M-R-16,M-R-16,M+R+16,M+R+16],fill=(18,19,22,255))
under.alpha_composite(ring)
over=Image.new('RGBA',(SZ,SZ),(0,0,0,0)); hd=ImageDraw.Draw(over)
hd.arc([M-R-12,M-R-12,M+R+12,M+R+12],200,290,fill=(255,255,255,170),width=4); hd.ellipse([M-R,M-R,M+R,M+R],outline=(255,255,255,70),width=2)
hd.rounded_rectangle([M+R-96,M-R-76,M+R+16,M-R-30],8,fill=(14,15,17,230))
hd.text((M+R-40,M-R-53),"2.5x",font=font('JetBrainsMono-Bold.ttf',30),fill=(255,255,255),anchor='mm')
vg=1-0.12*np.clip((np.hypot((xx-W/2)/(W/2),(yy-H/2)/(H/2))-0.6),0,1)**1.5
base=Image.fromarray(np.clip(np.asarray(bg.convert('RGB')).astype(np.float32)*vg[...,None],0,255).astype('uint8'))
# ---- overlays drawn after the camera (fixed on screen): hook, subtitles, caption plate
hf=font('InterDisplay-SemiBold.otf',72)
SUBF=font('Inter-Medium.otf',40); SUBBOT=1528
def wrap(t):
    words=t.split(); lines=[]; cur=''
    for w_ in words:
        tt=(cur+' '+w_).strip()
        if SUBF.getlength(tt)<=740 or not cur: cur=tt
        else: lines.append(cur); cur=w_
    lines.append(cur); return lines
SUBS=[]
for o in NAR:
    ln=wrap(o['text']); assert len(ln)<=2,ln
    bw=int(max(SUBF.getlength(l) for l in ln))+48; bh=len(ln)*48+28
    im=Image.new('RGBA',(bw,bh),(0,0,0,0)); dd=ImageDraw.Draw(im); dd.rounded_rectangle([0,0,bw-1,bh-1],16,fill=(14,15,17,214))
    for i,l in enumerate(ln): dd.text((24,14+i*48),l,font=SUBF,fill=(255,255,255))
    SUBS.append((im,450-bw//2,SUBBOT-bh))
CP=(50,1270,850,1398)
cap=Image.new('RGBA',(CP[2]-CP[0],CP[3]-CP[1]),(0,0,0,0)); cdr=ImageDraw.Draw(cap)
cdr.rounded_rectangle([0,0,799,127],14,fill=(14,15,17,222)); cdr.rectangle([0,0,4,127],fill=SIG)
cdr.text((32,14),"TAB. XIII",font=font('JetBrainsMono-Bold.ttf',50),fill=(255,255,255))
cdr.text((330,18),"Prospect of Stonehenge",font=font('Inter-Medium.otf',26),fill=(255,255,255))
cdr.text((330,52),"from the Southwest, p. 24",font=font('Inter-Medium.otf',26),fill=(255,255,255))
cdr.text((32,72),"Stukeley, 1740 | archive.org b30448554 | scan 0067",font=font('JetBrainsMono-Medium.ttf',20),fill=(190,196,203))
cdr.text((32,99),"The scans are real. The orange marks and 2.5x loupe are ours.",font=font('Inter-Medium.otf',22),fill=(255,150,110))
# ---- easing
def cl(u): return min(1.0,max(0.0,u))
def seg(t,a,b): return cl((t-a)/(b-a))
def oc(u): return 1-(1-u)**3
def oq(u): return 1-(1-u)**2.5
def sm_(u): return u*u*(3-2*u)
s2a=S[2][0]; s2b=S[3][0]; s3=S[4][0]; s4=S[5][0]; s5=S[6][0]
T=dict(in0=s2a, in1=s2a+2.0,                 # loupe glides in, over the lintel
       el0=s2b+0.25, el1=s2b+1.15,           # ellipse draws; closes (tick) at el1
       elf0=s3-0.05, elf1=s3+0.35,           # ellipse fades
       mv0=s3+0.2, mv1=s3+1.8,               # loupe glides down to the figures
       mk0=s3+1.8, mk1=s3+2.5,               # new mark draws on
       lf0=s4-0.05, lf1=s4+0.65,             # loupe fades away
       pr0=s4+0.35, pr1=s4+1.45,             # ring on the plan plate draws
       cm0=s4, cm1=s4+3.4,                   # camera eases towards the plan
       prf0=s5-0.1, prf1=s5+0.4,             # plan ring fades
       cap0=s5, cap1=s5+0.9)                 # caption plate eases in
json.dump({k:round(v,3) for k,v in T.items()},open('timeline.json','w'),indent=1)
P0=np.array([300.,990.]); PM=np.array([430.,1075.])
def loupe_pos(t):
    if t<T['mv0']:
        u=oq(seg(t,T['in0'],T['in1'])); return (1-u)**2*P0+2*(1-u)*u*PM+u*u*L1
    u=sm_(seg(t,T['mv0'],T['mv1'])); mid=np.array([L1[0]-40,(L1[1]+L2[1])/2-20])
    return (1-u)**2*L1+2*(1-u)*u*mid+u*u*L2
def ellipse_ov(cxl,cyl,axx,ayy,pe,alpha):
    Sx=ss; ov=Image.new('RGBA',(2*R*Sx,2*R*Sx),(0,0,0,0)); od=ImageDraw.Draw(ov)
    N=max(2,int(240*pe)+2); a_=-math.pi/2+2*math.pi*pe*np.linspace(0,1,N)
    pts=[((R+cxl+axx*math.cos(a))*Sx,(R+cyl+ayy*math.sin(a))*Sx) for a in a_]
    col=SIG+(int(255*alpha),)
    od.line(pts,fill=col,width=5*Sx,joint='curve')
    for p in (pts[0],pts[-1]): od.ellipse([p[0]-2.5*Sx,p[1]-2.5*Sx,p[0]+2.5*Sx,p[1]+2.5*Sx],fill=col)
    return ov.resize((2*R,2*R),Image.LANCZOS)
def frame(n):
    t=n/FPS; im=base.copy()
    fade=oc(seg(t,T['in0'],T['in0']+0.4))*(1-oc(seg(t,T['lf0'],T['lf1'])))
    if fade>0:
        px,py=loupe_pos(t); px=int(round(px)); py=int(round(py))
        x0=(px-PX)*MAG-R; y0=(py-PY)*MAG-R
        c=np.asarray(master.transform((2*R,2*R),Image.AFFINE,(1,0,x0,0,1,y0),Image.BICUBIC)).astype(np.float32)*lensvig
        lens=Image.fromarray(np.clip(c,0,255).astype('uint8')).convert('RGBA')
        # mark 1: lintel ellipse (world-anchored: lens-local offset from the lens centre)
        pe=sm_(seg(t,T['el0'],T['el1'])); al=1-sm_(seg(t,T['elf0'],T['elf1']))
        if pe>0 and al>0:
            e=(L1-np.array([px,py]))*MAG
            lens.alpha_composite(ellipse_ov(lx+e[0],ly+e[1],ax,ay,pe,al))
        # mark 2: figures
        pf=sm_(seg(t,T['mk0'],T['mk1']))
        if pf>0:
            e=(L2-np.array([px,py]))*MAG
            lens.alpha_composite(ellipse_ov(mx2+e[0],my2+e[1],ax2,ay2,pf,1.0))
        lm=mask.point(lambda v:int(v*fade)) if fade<1 else mask
        def fa(s_):
            if fade>=1: return s_
            s_=s_.copy(); s_.putalpha(s_.split()[3].point(lambda v:int(v*fade))); return s_
        u_=fa(under); o_=fa(over); pos=(px-M,py-M)
        im.paste(u_.convert('RGB'),pos,u_.split()[3])
        im.paste(lens.convert('RGB'),(px-R,py-R),lm)
        im.paste(o_.convert('RGB'),pos,o_.split()[3])
    # plan plate ring (world)
    pp=sm_(seg(t,T['pr0'],T['pr1'])); pa=1-sm_(seg(t,T['prf0'],T['prf1']))
    if pp>0 and pa>0:
        ov=Image.new('RGBA',(W,H),(0,0,0,0)); od=ImageDraw.Draw(ov)
        tot=pp*4; pts=[RING[0]]
        for i in range(4):
            f=cl(tot-i)
            if f<=0: break
            a_,b_=RING[i],RING[i+1]; pts.append((a_[0]+(b_[0]-a_[0])*f,a_[1]+(b_[1]-a_[1])*f))
        col=SIG+(int(255*pa),); od.line(pts,fill=col,width=5,joint='curve')
        for p in (pts[0],pts[-1]): od.ellipse([p[0]-3,p[1]-3,p[0]+3,p[1]+3],fill=col)
        im=im.convert('RGBA'); im.alpha_composite(ov); im=im.convert('RGB')
    # camera: slow push-in 1.00 -> 1.06 that never stops; focal point eases toward the plan plate
    u=t/DUR; s=1+0.06*(0.25*u+0.75*sm_(u))
    k=sm_(seg(t,T['cm0'],T['cm1'])); fx=540+(400-540)*k; fy=900+(820-900)*k
    im=im.transform((W,H),Image.AFFINE,(1/s,0,fx-fx/s,0,1/s,fy-fy/s),Image.BICUBIC)
    im=im.convert('RGBA')
    # caption plate (fixed on screen)
    pc=oc(seg(t,T['cap0'],T['cap1']))
    if pc>0:
        c2=cap.copy(); c2.putalpha(c2.split()[3].point(lambda v:int(v*pc))); im.alpha_composite(c2,(CP[0],CP[1]+int(round((1-pc)*24))))
    # subtitles: 0.15 s fade in/out
    for (sb,(a,b)) in zip(SUBS,S):
        al=min(seg(t,a,a+0.15),1-seg(t,b,b+0.15))
        if al>0:
            s2=sb[0].copy(); s2.putalpha(s2.split()[3].point(lambda v:int(v*al))); im.alpha_composite(s2,(sb[1],sb[2]))
    im=im.convert('RGB'); dd=ImageDraw.Draw(im)   # hook: fixed, drawn last
    dd.text((60,84),"What did Stonehenge",font=hf,fill=INK); dd.text((60,170),"look like in 1740?",font=hf,fill=INK); dd.line([60,268,160,268],fill=SIG,width=5)
    return n,im.tobytes()
if __name__=='__main__':
    ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
      '-c:v','libx264','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart','-an','film_silent.mp4'],stdin=subprocess.PIPE)
    keep={int(round(i)) for i in np.linspace(0,NF-1,8)}; thumbs={}
    with Pool(4) as p:
        for n,b in p.imap(frame,range(NF),chunksize=4):
            ff.stdin.write(b)
            if n in keep: thumbs[n]=Image.frombytes('RGB',(W,H),b).resize((360,640),Image.LANCZOS)
            if n%60==0: print(n,flush=True)
    ff.stdin.close(); ff.wait()
    strip=Image.new('RGB',(360*8,640))
    for i,k in enumerate(sorted(thumbs)): strip.paste(thumbs[k],(360*i,0))
    strip.save('film_strip.jpg',quality=88)
