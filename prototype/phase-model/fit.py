import json,numpy as np,tifffile
from scipy.optimize import least_squares
exec(open('cls.py').read().split('for r in sorted')[0])
cand=[r for r in rows if 13.4<np.hypot(*(r[1]-c0))<19 and r[2]>2 and r[4]=='']
P=np.array([r[1] for r in cand])
f=lambda q:np.hypot(P[:,0]-q[0],P[:,1]-q[1])-q[2]
q=least_squares(f,[c0[0],c0[1],16]).x;print(q,len(cand),np.round(f(q),2))
res=f(q);keep=np.abs(res)<1.6
q=least_squares(lambda q:(np.hypot(P[keep,0]-q[0],P[keep,1]-q[1])-q[2]),q).x;print(q,keep.sum())
cx,cy,R=q
for k in range(30):
  pass
ang=np.degrees(np.arctan2(P[:,1]-cy,P[:,0]-cx))
print(sorted(np.round(ang[keep]).astype(int)))
ph=np.degrees(np.arctan2(P[keep,1]-cy,P[keep,0]-cx))
best=min(np.arange(0,12,0.25),key=lambda p:np.sum(np.abs(((ph-p+6)%12)-6)))
print('phase',best)
from scipy.spatial import cKDTree
t=cKDTree(pts[:,:2]);
for k in range(30):
    a=np.radians(best+12*k);x=cx+R*np.cos(a);y=cy+R*np.sin(a)
    i=t.query_ball_point([x,y],1.3);g=dtm[int(round(144999.5-y)),int(round(x-410000.5))]
    z=pts[i,2]-g
    d=[np.hypot(*(r[1]-[x,y])) for r in rows]; j=int(np.argmin(d))
    print(k,round(best+12*k),'n=%d maxh=%.1f n>2.5=%d'%(len(i),z.max() if len(i) else 0,(z>2.5).sum()),'osm %.1f m h=%.1f'%(d[j],rows[j][3]))
