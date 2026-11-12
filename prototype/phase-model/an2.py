import json, numpy as np, tifffile
from matplotlib.path import Path
D='/tmp/claude-0/-home-user-lumieralight/34561104-772d-5286-9a85-b273e18c62c0/scratchpad/history/data/lidar/'
pts=np.load('pts_window.npy')
dtm=tifffile.imread(D+'SU14sw_DTM_1m.tif'); dsm=tifffile.imread(D+'DSM_SU1040_P_11780_20210404_20210404.tif')
print(dtm.shape,dsm.shape,dtm.dtype)
def samp(a,x,y,x0=410000.5,y0=144999.5):
    col=np.round(x-x0).astype(int); row=np.round(y0-y).astype(int); return a[row,col]
# local ground: median DTM within 3m-of-stone ring? use point ground class z near
W=json.load(open('osm_ways.json'))
S=[w for w in W if w['tags'].get('natural')=='stone' and w['closed']]
res=[]
for w in S:
    poly=np.array(w['pts']); c=poly[:-1].mean(0)
    p=Path(poly)
    # buffer polygon by 0.3m
    inside=p.contains_points(pts[:,:2],radius=-0.0)
    # fallback: points within 0.5 m of the polygon
    cen=poly[:-1].mean(0); 
    near=p.contains_points(pts[:,:2],radius=0.4)|p.contains_points(pts[:,:2],radius=-0.4)
    g=samp(dtm,np.array([c[0]]),np.array([c[1]]))[0]
    s=samp(dsm,np.array([c[0]]),np.array([c[1]]))[0]
    zz=pts[near,2]
    # DSM max within footprint bbox
    xs=np.arange(np.floor(poly[:,0].min()),np.ceil(poly[:,0].max())+1); ys=np.arange(np.floor(poly[:,1].min()),np.ceil(poly[:,1].max())+1)
    gx,gy=np.meshgrid(xs,ys); m=p.contains_points(np.c_[gx.ravel()+0.0,gy.ravel()+0.0],radius=0.6)|p.contains_points(np.c_[gx.ravel(),gy.ravel()],radius=-0.6)
    dmax=samp(dsm,gx.ravel()[m],gy.ravel()[m]).max() if m.any() else np.nan
    res.append((w['id'],c,g,s,dmax,len(zz),(zz.max()-g) if len(zz) else np.nan))
c0=np.array([412245.0,142194.0])
for r in sorted(res,key=lambda r:np.hypot(*(r[1]-c0))):
    print(r[0],'r=%.1f dtm=%.2f dsm@c=%.2f dsmmax-g=%.2f npts=%d ptmax-g=%.2f'%(np.hypot(*(r[1]-c0)),r[2],r[3],r[4]-r[2],r[5],r[6]))
