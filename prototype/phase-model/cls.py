import json,numpy as np
from matplotlib.path import Path
W=json.load(open('osm_ways.json'))
pts=np.load('pts_window.npy')
import tifffile
dtm=tifffile.imread('../../data/lidar/SU14sw_DTM_1m.tif')
S=[w for w in W if w['tags'].get('natural')=='stone' and w['closed']]
c0=np.array([412245.,142194.])
rows=[]
for w in S:
    P=np.array(w['pts']);c=P[:-1].mean(0);x,y=P[:,0],P[:,1]
    a=0.5*abs(np.dot(x[:-1],y[1:])-np.dot(x[1:],y[:-1]))
    p=Path(P);m=p.contains_points(pts[:,:2],radius=0.4)|p.contains_points(pts[:,:2],radius=-0.4)
    g=dtm[int(round(144999.5-c[1])),int(round(c[0]-410000.5))]
    h=pts[m,2].max()-g if m.any() else 0
    rows.append((w['id'],c,a,h,w['tags'].get('name','')))
for r in sorted(rows,key=lambda r:np.arctan2(*(r[1]-c0)[::-1])):
    d=r[1]-c0;print(r[0],'r=%.1f ang=%4.0f area=%.1f h=%.1f %s'%(np.hypot(*d),np.degrees(np.arctan2(d[1],d[0])),r[2],r[3],r[4]))
