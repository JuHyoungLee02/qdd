import re, subprocess
log = open('D:/qdd/docs/user-log.md', encoding='utf-8').read()
def norm(s):
    s = s.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
    return re.sub(r'\s+', ' ', s).strip()
L = norm(log)
FILES=['D:/qdd/docs/design/SUMMARY.md','D:/qdd/docs/design/STAGE2-CLOSE.md','D:/qdd/docs/plan.md','D:/qdd/docs/design/00-interfaces.md']
diff = chr(10).join('+'+l for f in FILES for l in open(f,encoding='utf-8').read().splitlines())
n = bad = 0
for line in diff.splitlines():
    if not line.startswith('+') or line.startswith('+++') or '[사용자]' not in line:
        continue
    body = norm(line[1:])
    if body.startswith('> 개정'):
        continue
    body = re.sub(r'\(user-log[^)]*\)*\)', '', body).replace('**', '')
    quotes = re.findall(r'"([^"]{6,})"', body) + re.findall(r"'([^']{6,})'", body)
    if not quotes:
        # whole-line user statement: text after the tag
        m = re.search(r'\[사용자\]\*{0,2}\s*(.+)', body)
        quotes = [m.group(1)] if m else []
    for q in quotes:
        n += 1
        parts = [p.strip(' .*') for p in re.split(r'(?<=[.!?])\s+|…', q) if p.strip(' .*')]
        miss = [p for p in parts if p not in L]
        if miss:
            bad += 1
            print('LINE:', body[:110])
            for p in miss[:2]:
                print('   NOT IN LOG:', p[:110])
print('quotes checked', n, 'flagged', bad)
