import sys, glob, json
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import numpy as np
from collections import Counter
import diag as D
for ck in ('f35d','0.5'):
    rep=Counter(); tot=Counter(); epi=Counter(); ncap=0; zlist=[]
    for f in glob.glob(f'{D.R}/{ck}/none/*/*/result.json'):
        r=json.load(open(f)); S=D.sites(r)
        cap=r['end_reason']=='stage_cap_calls'; ncap+=cap
        runs=0; best=0
        for a,b in zip(S,S[1:]):
            if a['err'] is None: continue
            if a['out']['reached']: k='reach'
            elif a['out']['clipped']: k='clipped'
            else: k='<=15' if a['err']<=15 else ('15-30' if a['err']<=30 else '>30')
            tot[k]+=1; s=D.same_cmd(a,b); rep[k]+=s
            if k in ('15-30','<=15') and s: runs+=1; best=max(best,runs)
            else: runs=0
            if k=='15-30' and a['goal']: zlist.append(a['goal'][2]-(r['calls'][0]['truth']['tcp'][2]))
        if cap and best>=5: epi['cap eps with >=5 same cmd after 8-30mm near-miss']+=1
    print(ck,'ncap',ncap,{k:f'{rep[k]}/{tot[k]}' for k in tot},dict(epi))
