import json,re,collections,glob
ROOT='/Users/rock/code/upland-tools/'
def norm(s): return re.sub(r' 1$','',re.sub(r'[^a-z0-9]+',' ',s.lower()).strip())
bal=json.load(open(ROOT+'data/troves/rockdrigo/latest.json'))
STOCK={i[0]:i[2] for i in bal['items']}; FOUND=set(STOCK)
REC=collections.defaultdict(list)
for a,ing in bal['recipes']: REC[a].append(tuple(sorted((x,q) for x,q in ing)))
cs=json.load(open(ROOT+'data/troves/craft-sites.json'))['troves']; sr=json.load(open(ROOT+'data/troves/structure-recipes.json'))['structures']
QN=json.load(open(ROOT+'data/troves/places/4.json'))['structs']; QK={norm(n) for n in QN}
SITES=collections.defaultdict(set)
for t,v in cs.items():
    for ver in v['versions']:
        for a in ver['at']: SITES[(t,tuple(sorted((x,q) for x,q in ver['ing'])))].add(norm(a))
for c in json.load(open(ROOT+'data/troves/rockdrigo/crafts.json'))['crafts'] if False else []: pass
for f in glob.glob('/Users/rock/Downloads/trove-hunting-session-2026-11-1*.json'):
    for c in json.load(open(f))['crafts']: SITES[(c['recipe'],tuple(sorted((x,q) for x,q in c['ingredients'])))].add(norm(c['building']))
for b,d in sr.items():
    for t,names in d.items():
        for v in REC.get(t,[]):
            if sorted(x for x,_ in v)==sorted(names): SITES[(t,v)].add(norm(b))
def qs(t,v):
    if t=='Compass' and any(x=='Binoculars' for x,_ in v): return set()
    return SITES.get((t,v),set())&QK
def pl(item,n,stock,depth,path):
    miss=collections.Counter(); crafts=[]
    have=min(stock[item],n); stock[item]-=have; need=n-have
    while need>0:
        if item not in REC or item in path or depth<=0: miss[item]+=need; return miss,crafts
        best=None
        for v in REC[item]:
            if not qs(item,v): continue
            st=collections.Counter(stock); m=collections.Counter(); cr=[]
            for x,q in v:
                mm,cc=pl(x,q,st,depth-1,path+(item,)); m+=mm; cr+=cc
            sc=(sum(m.values()),len(cr))
            if best is None or sc<best[0]: best=(sc,m,cr,st,v)
        if best is None: miss[item]+=need; return miss,crafts
        _,m,cr,st,v=best; stock.clear(); stock.update(st); miss+=m; crafts+=cr+[(item,v)]; need-=1
    return miss,crafts
und=sorted(t for t in REC if t not in FOUND)
print(len(FOUND),'found;',len(und),'locked with a known recipe:',und)
rows=[]
for t in und:
    s=collections.Counter(STOCK); m,c=pl(t,1,s,8,()); rows.append((sum(m.values()),len(c),t,dict(m)))
for r in sorted(rows): print(r)
print('shared greedy:')
st=collections.Counter(STOCK); pend=list(und); tot=0
while pend:
    best=None
    for t in pend:
        s2=collections.Counter(st); m,c=pl(t,1,s2,8,())
        if not sum(m.values()) and c and (best is None or len(c)<best[0]): best=(len(c),t,s2)
    if not best: break
    n,t,s2=best; st=s2; pend.remove(t); tot+=n; print(' ',t,n,'cum',tot)
