"""What can be crafted in a city (or two) with the stock you hold now.

  python3 city_check.py 70 [87] -- 'Emerald,Sunday Dinner,Soulmate,Tesla Coil,Lifeline,Hourglass'

Prints, for each target, the crafts and the ingredients still missing when only the structures of those cities are used, then the best
order for all of them together (the first two are kept in place). Uses data/troves/rockdrigo/latest.json for stock and recipes.
"""
import json,re,collections,sys,itertools
ROOT='/Users/rock/code/upland-tools/'
def norm(s): return re.sub(r' 1$','',re.sub(r'[^a-z0-9]+',' ',s.lower()).strip())
bal=json.load(open(ROOT+'data/troves/rockdrigo/latest.json'))
STOCK={i[0]:i[2] for i in bal['items']}
REC=collections.defaultdict(list)
for a,ing in bal['recipes']: REC[a].append(tuple(sorted((x,q) for x,q in ing)))
cs=json.load(open(ROOT+'data/troves/craft-sites.json'))['troves']; sr=json.load(open(ROOT+'data/troves/structure-recipes.json'))['structures']
SITES=collections.defaultdict(set)
for t,v in cs.items():
    for ver in v['versions']:
        for a in ver['at']: SITES[(t,tuple(sorted((x,q) for x,q in ver['ing'])))].add(norm(a))
for b,d in sr.items():
    for t,names in d.items():
        for v in REC.get(t,[]):
            if sorted(x for x,_ in v)==sorted(names): SITES[(t,v)].add(norm(b))
import glob
for f in glob.glob('/Users/rock/Downloads/trove-hunting-session-2026-*.json'):   # recipes seen in your own crafts (the exports kept in Downloads)
    for c in json.load(open(f)).get('crafts',[]): SITES[(c['recipe'],tuple(sorted((x,q) for x,q in c['ingredients'])))].add(norm(c['building']))
V=lambda *a:tuple(sorted(a))
SITES[('Chisel Set',V(('Iron Ore',2),('Twine',1)))]|={'art gallery','art museum'}
SITES[('Holiday Ham',V(('Pork',5),('Honey',5),('Hooray',5)))]|={'community center'}
SITES[('Holiday Ham',V(('Maple Syrup',1),('Charcoal',1),('Cheers',1)))]|={'butcher shop'}
args=sys.argv[1:]; sep=args.index('--') if '--' in args else len(args)
CITIES=[int(x) for x in args[:sep]]; TARGETS=[x.strip() for x in (args[sep+1] if len(args)>sep+1 else 'Emerald,Sunday Dinner,Soulmate,Tesla Coil,Lifeline,Hourglass').split(',')]
K=set()
import glob
if CITIES==[0]:
    for f in glob.glob(ROOT+'data/troves/places/*.json'): K|={norm(n) for n in json.load(open(f))['structs']}
for c in CITIES:
    if c: K|={norm(n) for n in json.load(open(ROOT+'data/troves/places/%d.json'%c))['structs']}
def sites(t,v):
    if t=='Compass' and any(x=='Binoculars' for x,_ in v): return set()
    return SITES.get((t,v),set())&K
def pl(item,n,stock,depth,path):
    miss=collections.Counter(); crafts=[]
    have=min(stock[item],n); stock[item]-=have; need=n-have
    while need>0:
        if item not in REC or item in path or depth<=0: miss[item]+=need; return miss,crafts
        best=None
        for v in REC[item]:
            if not sites(item,v): continue
            st=collections.Counter(stock); m=collections.Counter(); cr=[]
            for x,q in v:
                mm,cc=pl(x,q,st,depth-1,path+(item,)); m+=mm; cr+=cc
            sc=(sum(m.values()),len(cr))
            if best is None or sc<best[0]: best=(sc,m,cr,st,v)
        if best is None: miss[item]+=need; return miss,crafts
        _,m,cr,st,v=best; stock.clear(); stock.update(st); miss+=m; crafts+=cr+[(item,v)]; need-=1
    return miss,crafts
def need(ts):
    st=collections.Counter(STOCK); miss=collections.Counter(); cr=[]
    for t in ts:
        m,c=pl(t,1,st,8,()); miss+=m; cr+=c
    return miss,cr
if __name__=='__main__':
    print('cities',CITIES,'| structures',len(K))
    for t in TARGETS:
        m,c=need([t]); print('  %-14s crafts %3d  missing %s'%(t,len(c),dict(m) or '-'))
    import os
    if os.environ.get('NOPERM') or len(TARGETS)>7: sys.exit(0)
    head=TARGETS[:2]; rest=TARGETS[2:]; best=None
    for p in itertools.permutations(rest):
        m,c=need(head+list(p)); sc=sum(m.values())
        if best is None or sc<best[0]: best=(sc,dict(m),p,len(c))
    print('all together, best order:',list(head)+list(best[2]),'| crafts',best[3],'| missing',best[1] or '-')
