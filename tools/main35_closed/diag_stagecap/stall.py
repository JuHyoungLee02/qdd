import sys, glob, json
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import numpy as np
from collections import Counter
import diag as D
R=D.R
def clusters(pts, tol=15):
    cs=[]
    for p in pts:
        for c in cs:
            if np.linalg.norm(np.subtract(p,c))*1e3<=tol: break
        else: cs.append(p)
    return len(cs)
for ck in ('f35d','0.5'):
  for cond in ('none','ALL'):
    tot=Counter(); loopstart=[]; per=Counter()
    for f in sorted(glob.glob(f'{R}/{ck}/*/*/*/result.json')):
        p=f.split('/')
        if cond!='ALL' and p[-4]!=cond: continue
        r=json.load(open(f))
        if r['end_reason']!='stage_cap_calls': continue
        S=D.sites(r)
        ends=[x['tcp_after'] or x['tcp'] for x in S]
        # stalled from k: the end TCPs from k to the end fall in <=2 clusters (15 mm)
        k0=len(S)
        for k in range(len(S)-1,-1,-1):
            if clusters(ends[k:])<=2: k0=k
            else: break
        stall_len=len(S)-k0
        lab,x=D.classify(r,S)
        L=S[-10:]
        two=sum(1 for a,b in zip(L,L[2:]) if D.same_cmd(a,b))>=6 and sum(D.same_cmd(a,b) for a,b in zip(L,L[1:]))<=2
        tot['n']+=1
        tot['stall>=10']+= stall_len>=10
        tot['stall>=15']+= stall_len>=15
        tot['period2']+= two
        tot['stall>=10 & wrong_target']+= stall_len>=10 and lab['wrong_target']
        tot['stall>=10 & clip_block']+= stall_len>=10 and lab['clip_block']
        tot['not stalled & not wrong']+= stall_len<10 and not lab['wrong_target']
        tot['not stalled']+= stall_len<10
        if stall_len>=10: loopstart.append(k0+1)
        per[p[-3]]+=stall_len>=10
    print(ck,cond,dict(tot),'loop start call p50',float(np.median(loopstart)) if loopstart else None, dict(per))
