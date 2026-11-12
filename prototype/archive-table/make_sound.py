# Mix: loudnormed voice + code-made quiet cues + room tone -> mix.wav (48k stereo float). Levels set by measurement.
import numpy as np, soundfile as sf, subprocess, json, re
SR=48000; DUR=28.8; N=int(DUR*SR); T=json.load(open('timeline.json')); rng=np.random.default_rng(7)
def fade(x,a=0.02,b=0.05):
    x=x.copy(); fa=int(a*SR); fb=int(b*SR); x[:fa]*=np.linspace(0,1,fa); x[-fb:]*=np.linspace(1,0,fb); return x
def rms_db(x): return 20*np.log10(np.sqrt(np.mean(x**2))+1e-12)
def lp(x,fc):  # one-pole low pass
    a=np.exp(-2*np.pi*fc/SR); y=np.zeros_like(x); s=0.0
    for i,v in enumerate(x): s=a*s+(1-a)*v; y[i]=s
    return y
# ---- voice: resample to 48k, loudnorm two-pass to -16 LUFS, TP -2
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','voice_raw.wav','-ar',str(SR),'-ac','1','-t',str(DUR),'voice_48.wav'],check=True)
r=subprocess.run(['ffmpeg','-hide_banner','-i','voice_48.wav','-af','loudnorm=I=-16:TP=-3.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
m=json.loads(r[r.rindex('{'):r.rindex('}')+1])
af=f"loudnorm=I=-16:TP=-3.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','voice_48.wav','-af',af,'-ar',str(SR),'voice_ln.wav'],check=True)
v,_=sf.read('voice_ln.wav'); v=v[:N] if v.ndim==1 else v[:N,0]; v=np.pad(v,(0,N-len(v)))
vpk=np.abs(v).max(); print('voice peak dBFS',20*np.log10(vpk))
CUE_PEAK=vpk*10**(-14/20)   # every cue peaks 14 dB under the voice peak (brief: at least 12)
# ---- room tone: low table hum, 55/110/165 Hz + brown-ish noise, -48 dBFS RMS
t=np.arange(N)/SR
hum=np.sin(2*np.pi*55*t)+0.5*np.sin(2*np.pi*110*t+1)+0.18*np.sin(2*np.pi*165*t+2)
nz=lp(rng.normal(0,1,N),220)
room=hum/np.sqrt(np.mean(hum**2))*0.8+nz/np.sqrt(np.mean(nz**2))*0.6
room*=1+0.04*np.sin(2*np.pi*0.23*t)
room=fade(room,1.0,1.5); room*=10**(-48/20)/np.sqrt(np.mean(room**2)); print('room rms',rms_db(room))
def place(sig,t0):
    y=np.zeros(N); i=int(t0*SR); sig=sig[:max(0,N-i)]; y[i:i+len(sig)]=sig; return y
def swell(d,f0=1500,f1=2300):   # soft glassy swell: shimmering partials, bell envelope, noise-band
    n=int(d*SR); tt=np.arange(n)/SR; u=tt/d
    f=f0+(f1-f0)*u; ph=2*np.pi*np.cumsum(f)/SR
    x=np.sin(ph)+0.5*np.sin(2.76*ph+0.7)+0.3*np.sin(4.1*ph+1.9)
    x*=1+0.25*np.sin(2*np.pi*7*tt)
    nb=rng.normal(0,1,n); nb=nb-lp(nb,900); nb=lp(nb,3500); x+=0.5*nb/np.std(nb)
    env=np.sin(np.pi*u)**2; x*=env
    return x/np.abs(x).max()
def tick(d=0.12):               # very soft tick: short damped glass-wood click
    n=int(d*SR); tt=np.arange(n)/SR
    x=np.sin(2*np.pi*1850*tt)*np.exp(-tt*55)+0.5*np.sin(2*np.pi*3100*tt)*np.exp(-tt*80)
    x[:int(0.001*SR)]*=np.linspace(0,1,int(0.001*SR)); return x/np.abs(x).max()
def softthud(d=0.4):            # caption plate settling
    n=int(d*SR); tt=np.arange(n)/SR; x=np.sin(2*np.pi*110*tt)*np.exp(-tt*9)*np.minimum(1,tt/0.02); return x/np.abs(x).max()
cues=np.zeros(N)
def add(sig,t0,peak_rel=1.0): 
    global cues; cues+=place(fade(sig,0.02,0.06),t0)*CUE_PEAK*peak_rel
add(swell(2.0),T['in0'],1.0)                      # loupe glides in
add(tick(),T['el1']-0.02,0.9)                     # ellipse closes
add(swell(1.6,1900,1300),T['mv0'],0.7)            # loupe glides down
add(tick(),T['mk1']-0.02,0.8)                     # new mark closes
add(tick(),T['pr1']-0.02,0.8)                     # plan ring closes
add(softthud(),T['cap0']+0.35,0.6)                # caption plate settles
print('cue peak',20*np.log10(np.abs(cues).max()),'voice peak',20*np.log10(vpk))
mono=(v+room+cues)*10**(-1.8/20)   # dual-mono stereo reads +3 LU: bring the mix to -16 LUFS
pk=np.abs(mono).max(); print('mix peak dBFS',20*np.log10(pk))
sf.write('mix.wav',np.stack([mono,mono],1).astype(np.float32),SR,subtype='FLOAT')
