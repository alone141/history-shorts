import json, numpy as np
W=json.load(open('osm_ways.json'))
S=[w for w in W if w['tags'].get('natural')=='stone' and w['closed']]
print(len(S))
rows=[]
for w in S:
    a=np.array(w['pts'][:-1]); c=a.mean(0)
    x,y=a[:,0],a[:,1]; ar=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(np.roll(x,-1),y))
    # long axis via PCA
    d=a-c; u,s,vt=np.linalg.svd(d,full_matrices=False)
    ext=[np.ptp(d@vt[0]),np.ptp(d@vt[1])]
    rows.append((w['id'],c,ar,ext,np.degrees(np.arctan2(vt[0][1],vt[0][0]))%180,w['tags'].get('name',''),w['tags'].get('ref','')))
c0=np.array([412245.0,142194.0])
for r in sorted(rows,key=lambda r:np.hypot(*(r[1]-c0))):
    dd=r[1]-c0
    print(r[0],'r=%.2f az=%.0f area=%.2f ext=%.1fx%.1f ax=%.0f'%(np.hypot(*dd),np.degrees(np.arctan2(dd[0],dd[1]))%360,r[2],r[3][0],r[3][1],r[4]),r[5],r[6])
