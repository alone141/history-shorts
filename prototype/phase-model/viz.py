import json,numpy as np,tifffile,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
S=json.load(open('scene.json'));pts=np.load('pts_window.npy');dtm=tifffile.imread('../../data/lidar/SU14sw_DTM_1m.tif')
cx,cy=S['cx'],S['cy']
gz=dtm[np.round(144999.5-pts[:,1]).astype(int),np.round(pts[:,0]-410000.5).astype(int)]
h=pts[:,2]-gz;x=pts[:,0]-cx;y=pts[:,1]-cy
m=(np.hypot(x,y)<24)&(h>1.0)&(h<8)
fig=plt.figure(figsize=(9,9));plt.scatter(x[m],y[m],c=h[m],s=14,cmap='viridis');plt.colorbar()
for s in S['stones']:
    p=np.array(s['poly']);plt.plot(p[:,0],-p[:,1],'r-',lw=.6)
for sl in S['slots']:
    a=np.radians(sl['ang']);plt.text(S['R']*np.cos(a)*1.25,S['R']*np.sin(a)*1.25,str(sl['i']),color='k',ha='center')
plt.axis('equal');plt.xlim(-24,24);plt.ylim(-24,24);plt.savefig('viz.png',dpi=80)
