import xml.etree.ElementTree as ET, json, sys, math
from pyproj import Transformer
H='/tmp/claude-0/-home-user-lumieralight/34561104-772d-5286-9a85-b273e18c62c0/scratchpad/history/data/osm/stonehenge_osm.xml'
t=Transformer.from_crs(4326,27700,always_xy=True)
r=ET.parse(H).getroot()
nodes={n.get('id'):t.transform(float(n.get('lon')),float(n.get('lat'))) for n in r.iter('node')}
out=[]
for w in r.iter('way'):
    tags={x.get('k'):x.get('v') for x in w.findall('tag')}
    pts=[nodes[n.get('ref')] for n in w.findall('nd')]
    closed=w.findall('nd')[0].get('ref')==w.findall('nd')[-1].get('ref')
    out.append(dict(id=w.get('id'),tags=tags,pts=pts,closed=closed))
json.dump(out,open('osm_ways.json','w'))
for o in out:
    p=o['pts']; 
    if len(p)>2 and o['closed']:
        import numpy as np
        a=np.array(p); c=a[:-1].mean(0)
        x,y=a[:,0],a[:,1]; area=0.5*abs(np.dot(x[:-1],y[1:])-np.dot(x[1:],y[:-1]))
    else: c=[0,0];area=0
    k={kk:v for kk,v in o['tags'].items() if kk in('name','ref','historic','natural','barrier','man_made','start_date','note','fixme','description')}
    print(o['id'],len(p),o['closed'],round(c[0],1),round(c[1],1),round(area,2),k)
