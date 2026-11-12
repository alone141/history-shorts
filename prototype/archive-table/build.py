import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
Image.MAX_IMAGE_PIXELS=None
A='/tmp/claude-0/-home-user-lumieralight/34561104-772d-5286-9a85-b273e18c62c0/scratchpad/history/data/archive/stukeley_1740/'
F='/home/user/lumieralight/fonts/'
W,H=1080,1920
SIG=(240,68,28); INK=(21,23,26)
rng=np.random.default_rng(3)
def font(n,s): return ImageFont.truetype(F+n,s)
# table: cool backlit surface
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
d=np.sqrt(((xx-W/2)/(W*0.75))**2+((yy-900)/(H*0.6))**2)
g=0.975-0.16*d**2
tab=np.stack([g*0.962,g*0.978,g*1.0],-1)*255
tab+=rng.normal(0,1.6,(H,W,1))
bg=Image.fromarray(np.clip(tab,0,255).astype('uint8')).convert('RGBA')
# dark desk edges + aluminium frame
dr=ImageDraw.Draw(bg)
dr.rectangle([0,0,W,H],outline=(38,41,46),width=14)
dr.rectangle([14,14,W-14,H-14],outline=(168,174,182),width=4)
def plate(i,w,x,y,rot):
    im=Image.open(A+f'jp2/b30448554_{i:04d}.jp2').convert('RGB')
    s=w/im.width
    t=im.resize((w,round(im.height*s)),Image.LANCZOS).convert('RGBA')
    # backlit paper: lift and cool slightly
    a=np.asarray(t).astype(np.float32); a[...,:3]=np.clip(a[...,:3]*1.06+6,0,255)
    t=Image.fromarray(a.astype('uint8'))
    r=t.rotate(rot,expand=True,resample=Image.BICUBIC)
    return im,s,r
def paste(base,r,x,y):
    al=r.split()[3]
    sh=Image.new('RGBA',base.size,(0,0,0,0))
    m=Image.new('L',base.size,0); m.paste(al,(x+10,y+16))
    m=m.filter(ImageFilter.GaussianBlur(14)).point(lambda v:int(v*0.34))
    sh.putalpha(m); base.alpha_composite(sh)
    m2=Image.new('L',base.size,0); m2.paste(al,(x+2,y+3)); m2=m2.filter(ImageFilter.GaussianBlur(3)).point(lambda v:int(v*0.3))
    s2=Image.new('RGBA',base.size,(0,0,0,0)); s2.putalpha(m2); base.alpha_composite(s2)
    base.alpha_composite(r,(x,y))
# plates (page 0059 plan, 0083 inward view, 0067 prospect)
_,_,r=plate(59,500,0,0,-4); paste(bg,r,40,310)
_,_,r=plate(83,560,0,0,3.5); paste(bg,r,500,325)
PW=980; PX=10; PY=722
im67,s67,r=plate(67,PW,0,0,0); paste(bg,r,PX,PY)
# loupe
MAG=2.5; R=230
bx,by=900,230   # browse coords of lens centre
cxm=bx/1400*7603; cym=by/734*3985
half=R/(MAG*s67)
crop=im67.crop((int(cxm-half),int(cym-half),int(cxm+half),int(cym+half))).resize((2*R,2*R),Image.LANCZOS)
cx=round(PX+cxm*s67); cy=round(PY+cym*s67)
ss=3
c=np.asarray(crop).astype(np.float32)
# gentle level for weak scan, backlit
c=np.clip((c-70)*1.18+14,0,255)
yy2,xx2=np.mgrid[0:2*R,0:2*R].astype(np.float32); rr=np.hypot(xx2-R,yy2-R)/R
c*= (1-0.10*rr**3)[...,None]
lens=Image.fromarray(c.astype('uint8')).convert('RGBA')
dl=ImageDraw.Draw(lens)
# mark: ellipse round the great lintel (measured from plate position: lintel centre browse 898,170, ~140x55)
lx=(898-bx)*PW/1400*MAG; ly=(170-by)*PW/1400*MAG
ax,ay=140*PW/1400*MAG/2+14, 55*PW/1400*MAG/2+14
dl.ellipse([R+lx-ax,R+ly-ay,R+lx+ax,R+ly+ay],outline=SIG,width=5)
mask=Image.new('L',(2*R*ss,2*R*ss),0); ImageDraw.Draw(mask).ellipse([0,0,2*R*ss-1,2*R*ss-1],fill=255)
mask=mask.resize((2*R,2*R),Image.LANCZOS)
# lens shadow
sm=Image.new('L',bg.size,0); sm.paste(mask,(cx-R+16,cy-R+26)); sm=sm.filter(ImageFilter.GaussianBlur(22)).point(lambda v:int(v*0.45))
sh=Image.new('RGBA',bg.size,(0,0,0,0)); sh.putalpha(sm); bg.alpha_composite(sh)
# acrylic skirt, black ring
ring=Image.new('RGBA',bg.size,(0,0,0,0)); rd=ImageDraw.Draw(ring)
rd.ellipse([cx-R-34,cy-R-34,cx+R+34,cy+R+34],fill=(235,242,248,120))
rd.ellipse([cx-R-16,cy-R-16,cx+R+16,cy+R+16],fill=(18,19,22,255))
bg.alpha_composite(ring)
bg.paste(lens,(cx-R,cy-R),mask)
hl=Image.new('RGBA',bg.size,(0,0,0,0)); hd=ImageDraw.Draw(hl)
hd.arc([cx-R-12,cy-R-12,cx+R+12,cy+R+12],200,290,fill=(255,255,255,170),width=4)
hd.ellipse([cx-R,cy-R,cx+R,cy+R],outline=(255,255,255,70),width=2)
bg.alpha_composite(hl)
# leader from ring through lens rim to caption
d2=ImageDraw.Draw(bg)
lyc=cy+ly+ay  # bottom of the mark ellipse
d2.line([cx+lx,cy+R+34,cx+lx,1262],fill=SIG,width=3)
d2.ellipse([cx+lx-8,cy+R+34-8,cx+lx+8,cy+R+34+8],fill=SIG)
# loupe magnification tag
d2.rounded_rectangle([cx+R-96,cy-R-76,cx+R+16,cy-R-30],8,fill=(14,15,17,230))
d2.text((cx+R-40,cy-R-53),"2.5x",font=font('JetBrainsMono-Bold.ttf',30),fill=(255,255,255),anchor='mm')
# hook
hf=font('InterDisplay-SemiBold.otf',72)
d2.text((60,84),"What did Stonehenge",font=hf,fill=INK)
d2.text((60,170),"look like in 1740?",font=hf,fill=INK)
d2.line([60,268,160,268],fill=SIG,width=5)
# caption plate
cap=Image.new('RGBA',bg.size,(0,0,0,0)); cd=ImageDraw.Draw(cap)
cd.rounded_rectangle([50,1262,850,1532],14,fill=(14,15,17,200))
cd.rectangle([50,1262,54,1532],fill=SIG)
bg.alpha_composite(cap)
d2=ImageDraw.Draw(bg)
d2.text((84,1282),"PLATE NUMBER, ENGRAVED",font=font('Inter-Medium.otf',24),fill=(205,210,216))
d2.text((82,1314),"TAB. XIII",font=font('JetBrainsMono-Bold.ttf',68),fill=(255,255,255))
d2.text((490,1326),"Prospect of Stonehenge",font=font('Inter-Medium.otf',27),fill=(255,255,255))
d2.text((490,1362),"from the Southwest, p. 24",font=font('Inter-Medium.otf',27),fill=(255,255,255))
d2.line([84,1416,816,1416],fill=(90,94,100),width=1)
d2.text((84,1430),"Stukeley, 1740 | archive.org b30448554 | scan 0067",font=font('JetBrainsMono-Medium.ttf',22),fill=(190,196,203))
d2.text((84,1462),"Real scans: nothing in them is redrawn or generated.",font=font('Inter-Medium.otf',24),fill=(255,255,255))
d2.text((84,1494),"The orange mark and 2.5x loupe are ours.",font=font('Inter-Medium.otf',24),fill=(255,128,90))
# evidence code strip (above caption plate is the lens; put under table frame, still <1536)
d2.text((60,1526),"",font=font('Inter-Medium.otf',22))
# vignette
v=np.asarray(bg).astype(np.float32)
vg=1-0.12*np.clip((np.hypot((xx-W/2)/(W/2),(yy-H/2)/(H/2))-0.6),0,1)**1.5
v[...,:3]*=vg[...,None]
out=Image.fromarray(np.clip(v,0,255).astype('uint8')).convert('RGB')
out.save('still.png')
