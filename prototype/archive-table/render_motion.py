# 5 s motion test: "the loupe comes down". Every value is a pure function of the frame number.
# Re-render: cd <this folder> && python3 render_motion.py   (writes motion.mp4 + strip.jpg)
import numpy as np, math, subprocess, os, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
Image.MAX_IMAGE_PIXELS=None
src=open('build.py').read()
A=re.search(r"^A='(.*)'",src,re.M).group(1); F='/home/user/lumieralight/fonts/'
W,H=1080,1920; FPS=30; NF=150
SIG=(240,68,28); INK=(21,23,26)
rng=np.random.default_rng(3)
def font(n,s): return ImageFont.truetype(F+n,s)
# ---- static scene: identical to build.py (table + plates), no hook/loupe/caption
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
_,_,r=plate(59,500,-4); paste(bg,r,40,310)
_,_,r=plate(83,560,3.5); paste(bg,r,500,325)
PW=980; PX=10; PY=722
im67,s67,r=plate(67,PW,0); paste(bg,r,PX,PY)
# ---- loupe constants (as build.py)
MAG=2.5; R=230; bx,by=900,230
cxm=bx/1400*7603; cym=by/734*3985
cx=round(PX+cxm*s67); cy=round(PY+cym*s67)
lx=(898-bx)*PW/1400*MAG; ly=(170-by)*PW/1400*MAG
ax,ay=140*PW/1400*MAG/2+14, 55*PW/1400*MAG/2+14
# high-res master of plate 67 at 2.5x the table scale, levelled once
MW=round(PW*MAG); master=im67.resize((MW,round(im67.height*MW/im67.width)),Image.LANCZOS)
master=Image.fromarray(np.clip((np.asarray(master).astype(np.float32)-70)*1.18+14,0,255).astype('uint8'))
y2,x2=np.mgrid[0:2*R,0:2*R].astype(np.float32); rr=np.hypot(x2-R,y2-R)/R; lensvig=(1-0.10*rr**3)[...,None]
ss=3
mask=Image.new('L',(2*R*ss,2*R*ss),0); ImageDraw.Draw(mask).ellipse([0,0,2*R*ss-1,2*R*ss-1],fill=255); mask=mask.resize((2*R,2*R),Image.LANCZOS)
# loupe sprites, centre at (M,M)
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
# caption: opaque final region + mask
CB=(50,1262,851,1533)
cap=bg.copy(); cc=Image.new('RGBA',bg.size,(0,0,0,0)); cd=ImageDraw.Draw(cc)
cd.rounded_rectangle([50,1262,850,1532],14,fill=(14,15,17,200)); cd.rectangle([50,1262,54,1532],fill=SIG); cap.alpha_composite(cc)
d2=ImageDraw.Draw(cap)
d2.text((84,1282),"PLATE NUMBER, ENGRAVED",font=font('Inter-Medium.otf',24),fill=(205,210,216))
d2.text((82,1314),"TAB. XIII",font=font('JetBrainsMono-Bold.ttf',68),fill=(255,255,255))
d2.text((490,1326),"Prospect of Stonehenge",font=font('Inter-Medium.otf',27),fill=(255,255,255))
d2.text((490,1362),"from the Southwest, p. 24",font=font('Inter-Medium.otf',27),fill=(255,255,255))
d2.line([84,1416,816,1416],fill=(90,94,100),width=1)
d2.text((84,1430),"Stukeley, 1740 | archive.org b30448554 | scan 0067",font=font('JetBrainsMono-Medium.ttf',22),fill=(190,196,203))
d2.text((84,1462),"Real scans: nothing in them is redrawn or generated.",font=font('Inter-Medium.otf',24),fill=(255,255,255))
d2.text((84,1494),"The orange mark and 2.5x loupe are ours.",font=font('Inter-Medium.otf',24),fill=(255,128,90))
vg=1-0.12*np.clip((np.hypot((xx-W/2)/(W/2),(yy-H/2)/(H/2))-0.6),0,1)**1.5
def vig(im): return Image.fromarray(np.clip(np.asarray(im.convert('RGB')).astype(np.float32)*vg[...,None],0,255).astype('uint8'))
base=vig(bg); capfull=vig(cap)
capreg=capfull.crop(CB)
cw,ch=CB[2]-CB[0],CB[3]-CB[1]
cm=Image.new('L',(cw*4,ch*4),0); cmd=ImageDraw.Draw(cm); cmd.rounded_rectangle([0,0,800*4,270*4],56,fill=255); cmd.rectangle([0,0,4*4+3,270*4],fill=255)
cm=cm.resize((cw,ch),Image.LANCZOS)
hf=font('InterDisplay-SemiBold.otf',72)
# ---- easing
def cl(u): return min(1.0,max(0.0,u))
def seg(t,a,b): return cl((t-a)/(b-a))
def oc(u): return 1-(1-u)**3
def oq(u): return 1-(1-u)**2.5
def sm_(u): return u*u*(3-2*u)
P0=np.array([300.,990.]); P2=np.array([float(cx),float(cy)]); P1=np.array([430.,1075.])
def loupe_pos(t):
    u=oq(seg(t,1.0,3.0)); return (1-u)**2*P0+2*(1-u)*u*P1+u*u*P2
def frame(n):
    t=n/FPS; im=base.copy()
    if t>=1.0:
        px,py=loupe_pos(t); px=int(round(px)); py=int(round(py))
        fade=oc(seg(t,1.0,1.4))
        x0=(px-PX)*MAG-R; y0=(py-PY)*MAG-R
        c=np.asarray(master.transform((2*R,2*R),Image.AFFINE,(1,0,x0,0,1,y0),Image.BICUBIC)).astype(np.float32)*lensvig
        lens=Image.fromarray(np.clip(c,0,255).astype('uint8')).convert('RGBA')
        pe=sm_(seg(t,3.0,3.5))
        if pe>0:
            S=ss; ov=Image.new('RGBA',(2*R*S,2*R*S),(0,0,0,0)); od=ImageDraw.Draw(ov)
            N=max(2,int(240*pe)+2); th=-math.pi/2+2*math.pi*pe*np.linspace(0,1,N)
            pts=[((R+lx+ax*math.cos(a))*S,(R+ly+ay*math.sin(a))*S) for a in th]
            od.line(pts,fill=SIG+(255,),width=5*S,joint='curve')
            for p in (pts[0],pts[-1]): od.ellipse([p[0]-2.5*S,p[1]-2.5*S,p[0]+2.5*S,p[1]+2.5*S],fill=SIG+(255,))
            lens.alpha_composite(ov.resize((2*R,2*R),Image.LANCZOS))
        lm=mask.point(lambda v:int(v*fade)) if fade<1 else mask
        def fa(s):
            if fade>=1: return s
            s=s.copy(); s.putalpha(s.split()[3].point(lambda v:int(v*fade))); return s
        u_=fa(under); o_=fa(over)
        pos=(px-M,py-M)
        im.paste(u_.convert('RGB'),pos,u_.split()[3])
        im.paste(lens.convert('RGB'),(px-R,py-R),lm)
        im.paste(o_.convert('RGB'),pos,o_.split()[3])
        # leader
        pl=oc(seg(t,3.45,3.8))
        if pl>0:
            dd=ImageDraw.Draw(im); y0l=cy+R+34; x=cx+lx
            dd.line([x,y0l,x,y0l+(1262-y0l)*pl],fill=SIG,width=3); dd.ellipse([x-8,y0l-8,x+8,y0l+8],fill=SIG)
    # caption plate: short rise and fade
    pc=oc(seg(t,3.6,4.4))
    if pc>0:
        dy=int(round((1-pc)*28)); m=cm.point(lambda v:int(v*pc))
        im.paste(capreg,(CB[0],CB[1]+dy),m)
    # camera: slow push-in, never stops (linear share + smoothstep share)
    u=t/5.0; s=1+0.04*(0.25*u+0.75*sm_(u))
    im=im.transform((W,H),Image.AFFINE,(1/s,0,540-540/s,0,1/s,900-900/s),Image.BICUBIC)
    # hook: fixed on screen
    dd=ImageDraw.Draw(im)
    dd.text((60,84),"What did Stonehenge",font=hf,fill=INK); dd.text((60,170),"look like in 1740?",font=hf,fill=INK); dd.line([60,268,160,268],fill=SIG,width=5)
    return im
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
  '-c:v','libx264','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart','-an','motion.mp4'],stdin=subprocess.PIPE)
keep={int(round(i)) for i in np.linspace(0,NF-1,6)}; thumbs={}
for n in range(NF):
    f=frame(n); ff.stdin.write(f.tobytes())
    if n in keep: thumbs[n]=f.resize((360,640),Image.LANCZOS)
ff.stdin.close(); ff.wait()
strip=Image.new('RGB',(360*6,640))
for i,k in enumerate(sorted(thumbs)): strip.paste(thumbs[k],(360*i,0))
strip.save('strip.jpg',quality=88)
