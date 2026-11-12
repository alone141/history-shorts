import laspy, numpy as np, time
P='/tmp/claude-0/-home-user-lumieralight/34561104-772d-5286-9a85-b273e18c62c0/scratchpad/history/data/lidar/SU1040_P_11780_20210404_20210404.laz'
cx,cy,R=412245,142194,130
out=[]
t=time.time()
with laspy.open(P) as f:
    print(f.header.point_count, f.header.mins, f.header.maxs)
    for ch in f.chunk_iterator(2_000_000):
        m=(abs(ch.x-cx)<R)&(abs(ch.y-cy)<R)
        if m.any(): out.append(np.c_[ch.x[m],ch.y[m],ch.z[m],ch.classification[m],ch.return_number[m]])
a=np.vstack(out); np.save('pts_window.npy',a); print(a.shape,time.time()-t, np.unique(a[:,3],return_counts=True))
