import json,math,re,glob,collections
ROOT='/Users/rock/code/upland-tools/';D=ROOT+'data/'
def norm(s): return re.sub(r' 1$','',re.sub(r'[^a-z0-9]+',' ',s.lower()).strip())
def rw(d):
    if d<=60: return 1.0
    if d>=100: return 0.0
    pts=[(60,1.0),(70,.63),(80,.46),(90,.3),(100,0.0)]
    for (d0,w0),(d1,w1) in zip(pts,pts[1:]):
        if d<=d1: return w0+(w1-w0)*(d-d0)/(d1-d0)
places=json.load(open(D+'troves/places.json')); fees=json.load(open(D+'troves/fees.json'))['fees']
hh=json.load(open(D+'troves/rockdrigo/hunts.json'))
emp={};evn={};q={}
for f in hh['finds']:
    if f[1]!=0: continue
    k=norm(hh['src'][f[2]][0]); evn[k]=evn.get(k,0)+1
    tn=hh['troves'][f[3]]; e=emp.setdefault(k,{}); e[tn]=e.get(tn,0)+1; q.setdefault(tn,[0,0]); q[tn][0]+=f[4]; q[tn][1]+=1
T=['Amethyst','Sand','Coal Lump','Quartz']; NEED={'Amethyst':329,'Sand':786,'Coal Lump':451,'Quartz':561}
kind={}
for r in places['troves']:
    for s in r[2]: kind.setdefault(norm(s),set()).add(r[0])
for t in T: print(t,'avg units/find',round(q[t][0]/q[t][1],2),'| structure kinds that can give it:',sum(1 for k,v in kind.items() if t in v))
def prob(k,t,ln): n=evn.get(k,0); return (emp.get(k,{}).get(t,0)+4.0/ln)/(n+4.0)
M=111320.0; r=100/M
res=[]
for f in glob.glob(D+'troves/places/*.json'):
    cd=json.load(open(f)); sn=[norm(x) for x in cd['structs']]
    rows=[{'pid':str(p[0]),'lat':p[2],'lng':p[3],'ks':[sn[k] for k in p[5] if sn[k] in kind]} for p in cd['props']]
    rows=[x for x in rows if x['ks']]
    if len(rows)<150: continue
    grid={}
    cell=lambda x:(math.floor(x['lat']/r),math.floor(x['lng']/(r/max(math.cos(math.radians(x['lat'])),.2))))
    for x in rows: grid.setdefault(cell(x),[]).append(x)
    sc=[]
    for x in rows:
        cy,cx=cell(x); ch=dict.fromkeys(T,0.0)
        for dy in(-1,0,1):
            for dx in(-1,0,1):
                for o in grid.get((cy+dy,cx+dx),[]):
                    d=0 if o is x else math.hypot((o['lat']-x['lat'])*M,(o['lng']-x['lng'])*M*math.cos(math.radians(x['lat'])))
                    w=rw(d)
                    if w<=0: continue
                    for k in o['ks']:
                        for t in T:
                            if t in kind[k]: ch[t]=1-(1-ch[t])*(1-w*prob(k,t,len(kind[k])))
        fee=fees.get(x['pid']); fee=fee if fee is not None else 40
        u=sum(ch[t]*q[t][0]/q[t][1]/NEED[t]*1000 for t in T)   # need-weighted
        sc.append((u/(1+fee/100),ch,fee))
    sc.sort(key=lambda z:-z[0]); top=sc[:100]
    tot={t:sum(c[t] for _,c,_ in top)*q[t][0]/q[t][1] for t in T}
    res.append((sum(tot[t]/NEED[t] for t in T),cd['name'],len(rows),tot,sum(f for _,_,f in top)))
res.sort(reverse=True)
print('city | props with a source | expected UNITS per 100 best visits: Amethyst/Sand/Coal/Quartz | fees for 100')
for s,n,np_,tot,fee in res[:10]: print(n,np_,[round(tot[t],1) for t in T],fee)
