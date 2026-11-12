# Synthesise each sentence (Kokoro, bm_fable, en-gb, 0.92), lay them out on the narration clock -> voice_raw.wav, narration.json
import json, os, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
V='/tmp/claude-0/-home-user-lumieralight/34561104-772d-5286-9a85-b273e18c62c0/scratchpad/history/voice/model/'
SENT=[(1,"In the 1720s, William Stukeley measured and drew Stonehenge."),
(1,"His book came out in 1740."),
(2,"This is his view from the south-west."),
(2,"Under the glass, every line is his engraver's."),
(3,"He drew visitors among the stones, so the page shows how large they are."),
(4,"On another plate he drew the circle complete: his own reconstruction."),
(5,"The scans are real."),
(5,"Only the orange marks are ours.")]
# plan plate title read from scan 0059: "The Geometrical Ground-plot of Stonehenge" (complete circle, ovals, reconstruction) -> circle-complete line
GAP=0.35; START=0.4; SR_OUT=48000
k=Kokoro(V+'kokoro-v1.0.onnx',V+'voices-v1.0.bin')
parts=[]
for b,t in SENT:
    a,sr=k.create(t,voice='bm_fable',speed=0.92,lang='en-gb'); a=np.asarray(a,dtype=np.float32)
    # trim silence at the ends so measured length = spoken length
    idx=np.where(np.abs(a)>0.03)[0]; a=a[max(0,idx[0]-int(0.02*sr)):idx[-1]+int(0.03*sr)]
    parts.append((b,t,a,sr)); print(b,round(len(a)/sr,2),t,flush=True)
sr=parts[0][3]
import sys
gaps=[float(x) for x in sys.argv[1:]] if len(sys.argv)>1 else []
t=START; out=[]; 
for i,(b,tx,a,_) in enumerate(parts):
    out.append(dict(beat=b,text=tx,start_s=round(t,3),end_s=round(t+len(a)/sr,3))); 
    t+=len(a)/sr+ (gaps[i] if i<len(gaps) else GAP)
n=int((out[-1]['end_s']+3)*sr); y=np.zeros(n,np.float32)
for o,(b,tx,a,_) in zip(out,parts):
    i=int(round(o['start_s']*sr)); f=int(0.01*sr); a=a.copy(); a[:f]*=np.linspace(0,1,f); a[-f:]*=np.linspace(1,0,f); y[i:i+len(a)]+=a
sf.write('voice_raw.wav',y,sr); json.dump(out,open('narration.json','w'),indent=1); print('end',out[-1]['end_s'])
