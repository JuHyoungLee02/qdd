import re, glob
BS = chr(92)
log = open('D:/qdd/docs/user-log.md', encoding='utf-8').read()

def norm(s):
    s = s.replace('``', '"').replace("''", '"').replace(BS + '%', '%').replace('~', ' ')
    s = s.replace('\u201c', '"').replace('\u201d', '"').replace('$' + BS + 'rightarrow$', '\u2192')
    return re.sub(r'\s+', ' ', s).strip()

L = norm(log)
n = bad = 0
key = BS + 'intent{'
for f in glob.glob('D:/qdd/paper/sec/*.tex') + ['D:/qdd/paper/fig/teaser.tex']:
    t = open(f, encoding='utf-8').read()
    k = 0
    while True:
        k = t.find(key, k)
        if k < 0:
            break
        i = k + len(key); d = 1; j = i
        while d:
            if t[j] == '{': d += 1
            elif t[j] == '}': d -= 1
            j += 1
        s = norm(t[i:j - 1]); n += 1; k = j
        parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+| / ', s) if p.strip()]
        miss = [p for p in parts if p.rstrip('.') not in L]
        if miss:
            bad += 1
            print(f.split('/')[-1].split(BS)[-1], '|', s[:100])
            for m in miss[:3]:
                print('   MISSING:', m[:120])
print('total', n, 'flagged', bad)
