"""One focused hunting file that does not hunt the same structure twice.

  hunt_route_dep.py <city id> <file tag> '{"Lens":30,"Sand":9}' [stops=50] ['["20616 Chase","Oso Ave"]']

A structure gives finds once per hour, and a stop reaches every structure within about 80 m, so two stops on the same block share
structures and the second one finds nothing. Here every structure (a kind on a property) is counted once per run: each stop is worth
only what is still untouched, using the same reach weights as the other planners. Stops whose address contains one of the last
words are left out (properties known to give nothing). Writes ~/Downloads/<tag>.csv (or $OUT/<tag>.csv).
"""
import json,math,re,collections,os,sys
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+'/';D=ROOT+'data/'
def norm(s): return re.sub(r' 1$','',re.sub(r'[^a-z0-9]+',' ',s.lower()).strip())
def rw(d):
    if d<=60: return 1.0
    if d>=100: return 0.0
    pts=[(60,1.0),(70,.63),(80,.46),(90,.3),(100,0.0)]
    for (d0,w0),(d1,w1) in zip(pts,pts[1:]):
        if d<=d1: return w0+(w1-w0)*(d-d0)/(d1-d0)
CID=int(sys.argv[1]); TAG=sys.argv[2]; NEED=json.loads(sys.argv[3]); NSTOPS=int(sys.argv[4]) if len(sys.argv)>4 else 50
EXCL=[x.lower() for x in (json.loads(sys.argv[5]) if len(sys.argv)>5 else [])]
CAL=0.35; K=3.0   # the model overstates real finds (about 0.35 in Los Angeles); K = weight of the model against the visits she made
places=json.load(open(D+'troves/places.json')); fees=json.load(open(D+'troves/fees.json'))['fees']; best=json.load(open(D+'troves/reach-best.json'))['best80']
cd=json.load(open(D+'troves/places/%d.json'%CID)); sn=[norm(x) for x in cd['structs']]
try: own=json.load(open(D+'helper/own/rockdrigo/%d.json'%CID))['stops']
except Exception: own={}
hh=json.load(open(D+'troves/rockdrigo/hunts.json'))
ev=collections.defaultdict(list)
for f in hh['finds']: ev[str(hh['props'][f[5]][0])].append((f[0],hh['troves'][f[3]],f[4]))
vis=collections.defaultdict(list)
for p,hs in ev.items():
    hs.sort(); cur=None; last=0
    for t,name,n in hs:
        if cur is None or t-last>90: cur=collections.Counter(); vis[p].append(cur)
        last=t; cur[name]+=n
emp={};evn={}
for f in hh['finds']:
    if f[1]!=0: continue
    k=norm(hh['src'][f[2]][0]); evn[k]=evn.get(k,0)+1
    e=emp.setdefault(k,{}); tn=hh['troves'][f[3]]; e[tn]=e.get(tn,0)+1
kind={}
for r in places['troves']:
    for s in r[2]: kind.setdefault(norm(s),set()).add(r[0])
def prob(k,t,ln): n=evn.get(k,0); return (emp.get(k,{}).get(t,0)+4.0/ln)/(n+4.0)
M=111320.0; R=100/M
rows=[{'pid':str(p[0]),'addr':p[1],'lat':p[2],'lng':p[3],'ks':[sn[k] for k in p[5] if sn[k] in kind]} for p in cd['props']]
rows=[x for x in rows if x['ks']]
for i,x in enumerate(rows): x['i']=i
# per property: chance one hunt of it gives each needed trove (every structure on it counts once), then the visits she really made
for x in rows:
    x['pr']={t:1-math.prod(1-prob(k,t,len(kind[k])) for k in x['ks'] if t in kind[k]) for t in NEED}
    v=vis.get(x['pid'],[]); n=len(v); obs=collections.Counter()
    for c in v:
        for t in NEED: obs[t]+=c.get(t,0)
    prior=sum(x['pr'][t]/NEED[t] for t in NEED)
    seen=sum(obs[t]/NEED[t] for t in NEED)
    x['n']=n; x['obs']=obs
    x['m']=CAL if prior<=0 else min(3.0,max(0.05,(seen+K*CAL*prior)/((n+K)*prior)))   # multiplier on the model for this property
grid={}
cell=lambda x:(math.floor(x['lat']/R),math.floor(x['lng']/(R/max(math.cos(math.radians(x['lat'])),.2))))
for x in rows: grid.setdefault(cell(x),[]).append(x)
for x in rows:
    cy,cx=cell(x); nb=[]
    for dy in(-1,0,1):
        for dx in(-1,0,1):
            for o in grid.get((cy+dy,cx+dx),[]):
                d=0 if o is x else math.hypot((o['lat']-x['lat'])*M,(o['lng']-x['lng'])*M*math.cos(math.radians(x['lat'])))
                w=rw(d)
                if w>0: nb.append((o,w,d))
    x['nb']=nb
    b=best.get(x['pid']); x['stand'],x['fee']=(str(b[0]),b[1]) if b else (x['pid'],fees.get(x['pid']))
    o=own.get(x['pid']); x['own']=o if o and o[2]<=150 else None
    x['key']=x['own'][0] if x['own'] else x['stand']
left=dict(NEED); cons=collections.defaultdict(float)
def gain(x):
    g=0.0
    for o,w,_ in x['nb']:
        free=1-cons[o['i']]
        if free<=1e-3: continue
        g+=w*free*o['m']*sum(o['pr'][t]*max(0,left[t])/NEED[t] for t in NEED)
    return g
def cost(x): return 0 if x['own'] else (x['fee'] if x['fee'] is not None else 50)
cand=[x for x in rows if not any(e in x['addr'].lower() for e in EXCL)]
picked=[]; got=collections.Counter()
while cand and len(picked)<NSTOPS:
    x=max(cand,key=lambda x:gain(x)/(1+cost(x)/100))
    if gain(x)<=1e-6: break
    picked.append(x); gx={}
    for o,w,_ in x['nb']:
        free=1-cons[o['i']]
        for t in NEED: got[t]+=w*free*o['m']*o['pr'][t]; left[t]-=w*free*o['m']*o['pr'][t]
        cons[o['i']]=1-free*(1-w)
    cand=[y for y in cand if y['key']!=x['key']]
# check: nothing in the file overlaps another stop
close=sum(1 for a in picked for b in picked if a is not b and any(o is b for o,w,_ in a['nb'] if w>=0.46))//2
print('stops',len(picked),'| stops sharing reach (within 80 m) with another stop:',close,'| visited before',sum(1 for x in picked if x['n']),'| fees',sum(cost(x) for x in picked),'free',sum(1 for x in picked if x['own']))
print('expected from one run of this file:',{t:round(got[t],1) for t in NEED},'| asked',NEED)
out=os.environ.get('OUT') or os.path.expanduser('~/Downloads')
with open(os.path.join(out,TAG+'.csv'),'w',encoding='utf-8',newline='') as f:
    f.write('name,property_id,city_id,order\n')
    for i,x in enumerate(picked,1):
        top=sorted(NEED,key=lambda t:-x['pr'][t]*x['m']/NEED[t])[:3]
        hit='/'.join(top)+(' | seen %dx'%x['n'] if x['n'] else '')
        if x['own']: label,pid='%s (own, free) -> ~%s m to %s [%s]'%(x['own'][1],x['own'][2],x['addr'],hit),x['own'][0]
        else: label,pid='%s (fee %s) [%s]'%(x['addr'],x['fee'] if x['fee'] is not None else '?',hit),x['stand']
        f.write('"'+label.replace('"',"'")+'",%s,%d,%d\n'%(pid,CID,i))
print('wrote',os.path.join(out,TAG+'.csv'))
