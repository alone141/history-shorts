import numpy as np
exec(open('fit.py').read().split("ph=np.degrees")[0].replace("print(","(lambda *a:0)("))
cand=[r for r in rows if 13.2<np.hypot(*(r[1]-[cx,cy]))<19 and r[2]>1.9 and r[4]=='']
print(len(cand))
for ph0 in [0]:
  pass
a=np.array([np.degrees(np.arctan2(r[1][1]-cy,r[1][0]-cx)) for r in cand])
for off in np.arange(0,12,1.0):
  cost=np.sum(np.abs(((a-off+6)%12)-6)); print(off,round(cost,1),end=' | ')
print()
