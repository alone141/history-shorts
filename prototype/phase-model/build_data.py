# builds scene.json from the OSM extract + LiDAR point cloud window + 1 m DTM
import json,numpy as np,tifffile,warnings,logging
from matplotlib.path import Path
from scipy.optimize import least_squares
H='/tmp/claude-0/-home-user-lumieralight/34561104-772d-5286-9a85-b273e18c62c0/scratchpad/history/data/'
W=json.load(open('osm_ways.json')); pts=np.load('pts_window.npy')
dtm=tifffile.imread(H+'lidar/SU14sw_DTM_1m.tif')
def gz(x,y): return dtm[int(round(144999.5-y)),int(round(x-410000.5))]
S=[w for w in W if w['tags'].get('natural')=='stone' and w['closed']]
stones=[]
for w in S:
    P=np.array(w['pts'])[:-1]; c=P.mean(0); x,y=P[:,0],P[:,1]
    a=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    p=Path(np.array(w['pts'])); m=p.contains_points(pts[:,:2],radius=0.4)|p.contains_points(pts[:,:2],radius=-0.4)
    h=float(pts[m,2].max()-gz(*c)) if m.any() else 0.0
    stones.append(dict(id=w['id'],name=w['tags'].get('name',''),P=P,c=c,area=a,h=h))
c0=np.array([412245.,142194.])
d0=lambda s:np.hypot(*(s['c']-c0))
cand=[s for s in stones if 13.4<d0(s)<19 and s['area']>2 and not s['name']]
Pc=np.array([s['c'] for s in cand]); f=lambda q:np.hypot(Pc[:,0]-q[0],Pc[:,1]-q[1])-q[2]
q=least_squares(f,[*c0,16]).x; k=np.abs(f(q))<1.6
q=least_squares(lambda q:np.hypot(Pc[k,0]-q[0],Pc[k,1]-q[1])-q[2],q).x; cx,cy,R=q
ang=lambda s:np.degrees(np.arctan2(s['c'][1]-cy,s['c'][0]-cx))
A=np.array([ang(s) for s in cand])[k]
ph=min(np.arange(0,12,.1),key=lambda p:np.sum(np.abs(((A-p+6)%12)-6)))
circ=[s for s in stones if 13.4<np.hypot(*(s['c']-[cx,cy]))<19.5 and s['area']>1.9 and not s['name']]
TALL=2.5
slotstate=['empty']*30; slotstones={i:[] for i in range(30)}
for s in circ:
    a=ang(s); i=int(round(((a-ph)%360)/12))%30; slotstones[i].append(s)
    if s['h']>=TALL: slotstate[i]='standing'
    elif slotstate[i]=='empty': slotstate[i]='fallen'
from scipy.spatial import cKDTree
tree=cKDTree(pts[:,:2])
cloudtall=[]
for i in range(30):
    a=np.radians(ph+12*i); x=cx+R*np.cos(a); y=cy+R*np.sin(a)
    ix=tree.query_ball_point([x,y],1.5); g=gz(x,y); n=int((pts[ix,2]-g>=3.0).sum()); cloudtall.append(n)
    if n>=2: slotstate[i]='standing'
print('cloud counts',cloudtall)
nstand=slotstate.count('standing'); nfall=slotstate.count('fallen')
# trilithon horseshoe: 10 uprights on a ring about circle centre (radius from the tall inner stones)
inner=[s for s in stones if d0(s)<9.5 and s['h']>=5 and not s['name']]
rin=float(np.median([np.hypot(*(s['c']-[cx,cy])) for s in inner]))
tri_ang=[-11-22*j for j in range(10)]
# bluestone ring radius from the small mapped stones at 10-13.6 m
small=[s for s in stones if 10.5<np.hypot(*(s['c']-[cx,cy]))<14 and s['area']<1.6 and s['h']<1.5 and not s['name']]
rblue=float(np.median([np.hypot(*(s['c']-[cx,cy])) for s in small]))
PR=40.0
def loc(p): return [float(p[0]-cx),float(-(p[1]-cy))]   # x east, z south
out=dict(cx=cx,cy=cy,R=R,phase=ph,rin=rin,rblue=rblue,plate=PR,nstand=nstand,nfall=nfall,
 slots=[dict(i=i,state=slotstate[i],ang=ph+12*i) for i in range(30)],tri_ang=tri_ang,
 stones=[dict(id=s['id'],name=s['name'],poly=[loc(p) for p in s['P']],h=s['h'],area=s['area'],
   r=float(np.hypot(*(s['c']-[cx,cy])))) for s in stones if np.hypot(*(s['c']-[cx,cy]))<PR-1],
 ditch=[[loc(p) for p in w['pts']] for w in W if w['tags'].get('barrier')=='ditch' and any(np.hypot(p[0]-cx,p[1]-cy)<PR+30 for p in w['pts'])],
 bank=[dict(closed=w['closed'],pts=[loc(p) for p in w['pts']]) for w in W if w['tags'].get('man_made')=='embankment' and any(np.hypot(p[0]-cx,p[1]-cy)<PR+30 for p in w['pts'])])
json.dump(out,open('scene.json','w'))
print('centre',cx,cy,'R',round(R,2),'phase',round(ph,1),'standing',nstand,'fallen',nfall,'empty',slotstate.count('empty'),'rin',round(rin,2),'rblue',round(rblue,2),len(small),len(inner))
print(''.join({'standing':'S','fallen':'f','empty':'.'}[x] for x in slotstate))
