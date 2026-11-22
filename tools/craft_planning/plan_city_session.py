import json,re,collections,math,glob,random,time,sys,os
# usage: plan_city_session.py <city id> '<City, ST>' 'Target 1,Target 2,...' [out.json]
CITY=int(sys.argv[1]); CITYNAME=sys.argv[2]; TARGETS_ARG=[x.strip() for x in sys.argv[3].split(',')]; OUTJSON=sys.argv[4] if len(sys.argv)>4 else 'data.json'
ROOT='/Users/rock/code/upland-tools/'
def norm(s): return re.sub(r' 1$','',re.sub(r'[^a-z0-9]+',' ',s.lower()).strip())
bal=json.load(open(ROOT+'data/troves/rockdrigo/latest.json'))
STOCK=collections.Counter({i[0]:i[2] for i in bal['items']}); LEVEL={i[0]:(i[3],i[4]) for i in bal['items']}
REC=collections.defaultdict(list)
for a,ing in bal['recipes']: REC[a].append(tuple(sorted((x,q) for x,q in ing)))
cs=json.load(open(ROOT+'data/troves/craft-sites.json'))['troves']; sr=json.load(open(ROOT+'data/troves/structure-recipes.json'))['structures']
q=json.load(open(ROOT+'data/troves/places/%d.json'%CITY)); QN=q['structs']; HOODS=q['hoods']; QK={norm(n) for n in QN}
sess=[c for f in glob.glob('/Users/rock/Downloads/trove-hunting-session-2026-11-*.json') for c in json.load(open(f))['crafts']]
SITES=collections.defaultdict(dict)
for t,v in cs.items():
    for ver in v['versions']:
        key=(t,tuple(sorted((x,qq) for x,qq in ver['ing'])))
        for a in ver['at']: SITES[key].setdefault(norm(a),'upxland')
for c in sess: SITES[(c['recipe'],tuple(sorted((x,qq) for x,qq in c['ingredients'])))][norm(c['building'])]='seen'
for b,d in sr.items():
    for t,names in d.items():
        for v in REC.get(t,[]):
            if sorted(x for x,_ in v)==sorted(names): SITES[(t,v)][norm(b)]='seen'
def qsites(t,v):
    if t=='Compass' and any(x=='Binoculars' for x,_ in v): return {}
    return {k:e for k,e in SITES.get((t,v),{}).items() if k in QK}
def kinds_of(item,v): return set(qsites(item,v))
def pl(item,n,stock,depth,path):
    miss=collections.Counter(); crafts=[]
    have=min(stock[item],n); stock[item]-=have; need=n-have
    while need>0:
        if item not in REC or item in path or depth<=0: miss[item]+=need; return miss,crafts
        best=None
        for v in REC[item]:
            if not qsites(item,v): continue
            st=collections.Counter(stock); m=collections.Counter(); cr=[]
            for x,qq in v:
                mm,cc=pl(x,qq,st,depth-1,path+(item,)); m+=mm; cr+=cc
            sc=(sum(m.values()),len(cr))
            if best is None or sc<best[0]: best=(sc,m,cr,st,v)
        if best is None: miss[item]+=need; return miss,crafts
        _,m,cr,st,v=best; stock.clear(); stock.update(st); miss+=m; crafts+=cr+[(item,v)]; need-=1
    return miss,crafts
TARGETS=TARGETS_ARG
V=lambda *a:tuple(sorted(a))
SITES[('Chisel Set',V(('Iron Ore',2),('Twine',1)))].update({'art gallery':'seen','art museum':'seen'})
SITES[('Holiday Ham',V(('Pork',5),('Honey',5),('Hooray',5)))].update({'community center':'seen'})
BUILDUP=bool(os.environ.get('BUILDUP'))   # BUILDUP=1: every craft the city can do now toward the targets (first targets get their ingredients first), nothing assumed
if BUILDUP:
    st0=collections.Counter(STOCK); raw_plan=[]; MISSING=collections.Counter(); ASSUMED={}
    for t in TARGETS:
        m,c=pl(t,1,st0,8,()); MISSING+=m; raw_plan+=[(i,v,'unlock '+t) for i,v in c]
    av=collections.Counter(STOCK); PLAN=[]; pend=list(raw_plan); prog=True
    while prog:
        prog=False
        for c in list(pend):
            it,v,pu=c
            if all(av[x]>=qq for x,qq in v):
                for x,qq in v: av[x]-=qq
                av[it]+=1; PLAN.append(c); pend.remove(c); prog=True
    print('planned',len(raw_plan),'doable now',len(PLAN),'| still missing for the targets',dict(MISSING))
else:
    # 1) what is really missing: try every order of the 6 targets, keep the one needing the fewest ingredients you do not hold
    import itertools
    best=None
    for perm in itertools.permutations(TARGETS):
        st=collections.Counter(STOCK); miss=collections.Counter(); plan=[]
        for t in perm:
            m,c=pl(t,1,st,8,()); miss+=m; st[t]+=1   # the crafted trove is yours to use as an ingredient later
            for x,qq in m.items(): pass
        tot=sum(miss.values())
        if best is None or (tot,len(plan))<best[0]: best=((tot,0),perm,dict(miss))
    print('best order',best)
    TARGETS=list(best[1]); ASSUMED=best[2]
    # replan with the missing units added to the stock (they are the ones assumed)
    for _ in range(6):
        S2=collections.Counter(STOCK)
        for k,v in ASSUMED.items(): S2[k]+=v
        st=collections.Counter(S2); extra=collections.Counter(); PLAN=[]
        for t in TARGETS:
            m,c=pl(t,1,st,8,()); extra+=m; PLAN+=[(i,v,'unlock '+t) for i,v in c]; st[t]+=1
        if not sum(extra.values()): break
        for k,v in extra.items(): ASSUMED[k]=ASSUMED.get(k,0)+v
    print('assumed',ASSUMED)
    for k,v in ASSUMED.items(): STOCK[k]+=v
print('crafts',len(PLAN))
# 2) properties
OWN=None
props={}
for p in q['props']:
    if HOODS[p[4]]=='HOWARD BEACH': continue
    ks={norm(QN[i]) for i in p[5]}
    props[str(p[0])]={'pid':str(p[0]),'addr':p[1],'lat':p[2],'lng':p[3],'hood':HOODS[p[4]],'kinds':ks,'raw':[QN[i] for i in p[5]]}
def km(a,b): return math.hypot((a['lat']-b['lat'])*110.57,(a['lng']-b['lng'])*111.32*math.cos(math.radians(a['lat'])))
VER={(str(c['prop']),norm(c['building'])) for c in sess}
BAD={('81313162700822','community center')}
fees0=json.load(open(ROOT+'data/troves/fees.json'))['fees']
need=[(it,v,kinds_of(it,v)) for it,v,_ in PLAN]; need_kinds=[n[2] for n in need]
COVER_SEED=os.environ.get('COVER_SEED','')
def scoreP(p,idxs):
    ks=set()
    for i in idxs:
        k=need_kinds[i]&p['kinds']
        if k: ks|=k
    ks={k for k in ks if (p['pid'],k) not in BAD}
    gain=sum(1 for i in idxs if (need_kinds[i]&p['kinds'])-{k for k in p['kinds'] if (p['pid'],k) in BAD})
    if not gain: return 0
    usedk=len(ks); noise=len(p['kinds'])-usedk
    pen=(4 if usedk<2 else 1)*noise
    fee=0 if p['pid']==OWN else (fees0.get(p['pid']) or 40)
    s=gain/(20+fee+pen)
    if any((p['pid'],k) in VER for k in ks): s*=1.4
    if COVER_SEED: s*=1+0.25*random.Random('%s%s'%(COVER_SEED,p['pid'])).random()   # COVER_SEED=n: a different (still greedy) stop cover; try a few when stops stay unscheduled
    return s
route=[]; cov=set(); unc=list(range(len(need)))
while unc:
    best=None
    for p in props.values():
        if p in route: continue
        if not any(need[i][2]&p['kinds'] for i in unc): continue
        sc=scoreP(p,unc)
        if best is None or sc>best[0]: best=(sc,p)
    if best is None: print('NO SITE',[need[i][0] for i in unc]); break
    route.append(best[1]); unc=[i for i in unc if not (need[i][2]&best[1]['kinds'])]
print('chosen',len(route))
def rest_ok(av,rest):
    a=collections.Counter(av)
    for j in rest:
        _,v,_=PLAN[j]
        for x,qq in v:
            if a[x]<qq: return False
            a[x]-=qq
        a[PLAN[j][0]]+=1
    return True
def sched(order):
    av=collections.Counter(STOCK); todo=list(range(len(PLAN))); used=[]; sc={}
    for si,p in enumerate(order):
        n=0; ch=True
        while ch:
            ch=False
            for i in list(todo):
                it,v,pu=PLAN[i]; ks=kinds_of(it,v)&p['kinds']
                if ks and all(av[x]>=qq for x,qq in v):
                    a2=collections.Counter(av)
                    for x,qq in v: a2[x]-=qq
                    a2[it]+=1
                    if not rest_ok(a2,[j for j in todo if j!=i]): continue
                    av=a2; todo.remove(i); n+=1; ch=True; sc.setdefault(si,[]).append((i,sorted(ks)[0]))
        if n: used.append(p)
    return todo,used,sc,av
def cost(order):
    todo,used,_,_=sched(order)
    return (len(todo),len(used),sum(0 if p['pid']==OWN else (fees0.get(p['pid']) or 40) for p in used))
random.seed(5); bestc=None; t0=time.time()
base=list(route)
for it in range(3000):
    if time.time()-t0>20: break
    o=base[:]; random.shuffle(o)
    c=cost(o)
    if bestc is None or c<bestc[0]: bestc=(c,o)
cur=bestc[1]; curc=bestc[0]; t1=time.time()
while time.time()-t1<20 and len(cur)>1:
    o=cur[:]; i=random.randrange(0,len(o)); p=o.pop(i); o.insert(random.randrange(0,len(o)+1),p)
    c=cost(o)
    if c<=curc: cur,curc=o,c
route=cur; print('best order',curc)
todo,used,sc,final_av=sched(route)
extra=0
while todo and extra<8:   # leftovers: extra stops (never a revisit)
    extra+=1; bp=None
    for allow in (False,True):
        for p in props.values():
            if (p in route) and not allow: continue
            if not any(kinds_of(PLAN[i][0],PLAN[i][1])&p['kinds'] for i in todo): continue
            s_=scoreP(p,todo)
            if bp is None or s_>bp[0]: bp=(s_,p)
        if bp: break
    if not bp: break
    route.append(dict(bp[1]) if bp[1] in route else bp[1]); todo,used,sc,final_av=sched(route)
print('unscheduled',[PLAN[i][0] for i in todo],'stops',len(used))
# 3) stop data
raw={}
for n in QN: raw.setdefault(norm(n),n)
consumed=collections.Counter()
for it,v,pu in PLAN:
    for x,qq in v: consumed[x]+=qq
scarce={x for x,c in consumed.items() if STOCK.get(x,0)-c<=2 and STOCK.get(x,0)>0}
needed_later=collections.Counter(); crafted_total=collections.Counter(it for it,_,_ in PLAN)
for it,v,pu in PLAN:
    for x,qq in v: needed_later[x]+=qq
targets_set=set(TARGETS)
fees_all=fees0
ALLP={}
for p_ in q['props']:
    if HOODS[p_[4]]=='HOWARD BEACH': continue
    ALLP[str(p_[0])]={'addr':p_[1],'lat':p_[2],'lng':p_[3],'hood':HOODS[p_[4]],'kinds':{norm(QN[i]) for i in p_[5]}}
def km2(a,b): return math.hypot((a['lat']-b['lat'])*110.57,(a['lng']-b['lng'])*111.32*math.cos(math.radians(a['lat'])))
placesrows={r[0]:r for r in json.load(open(ROOT+'data/troves/places.json'))['troves']}
bonus={t:{norm(k) for k in placesrows[t][5]} for t in ['Amethyst','Copper Nugget','Sandpaper','Fools Gold'] if t in placesrows}
routepids={p['pid'] for p in route}
seen_pid=set()
have=collections.Counter(STOCK); out=[]; unlocked=[]; si_out=0
for si,p in enumerate(route):
    if si not in sc: continue
    si_out+=1
    here=p['kinds']; before=collections.Counter(have); groups=collections.OrderedDict(); used_items=set()
    for i,kind in sc[si]:
        item,ver,pu=PLAN[i]; ev=SITES[(item,ver)].get(kind,'upxland'); used_items.add(item)
        g=groups.setdefault(kind,[])
        if g and g[-1]['key']==(item,ver,pu): g[-1]['count']+=1
        else:
            alts=[]
            for v2 in REC.get(item,[]):
                if v2==ver: continue
                alts.append({'ver':[[x,qq] for x,qq in v2],'warn':[x for x,qq in v2 if x in scarce or STOCK.get(x,0)<qq]})
            g.append({'hold':have[item],'plan_needs':needed_later[item]+(1 if item in targets_set else 0),'plan_makes':crafted_total[item],'item':item,'ver':[[x,qq,have[x]] for x,qq in ver],'count':1,'purpose':pu,'evidence':ev,'alts':alts,'key':(item,ver,pu)})
        for x,qq in ver: have[x]-=qq
        have[item]+=1
        if pu=='unlock '+item: unlocked.append((item,si_out))
    touched=sorted({x for g_ in groups.values() for s_ in g_ for x,_,_ in s_['ver']}|{s_['item'] for g_ in groups.values() for s_ in g_})
    delta=[[x,before[x],have[x]] for x in touched]
    glist=[]
    for kind,steps in groups.items():
        for s_ in steps:
            s_.pop('key',None); s_['need']=[[x,qq*s_['count'],h] for x,qq,h in s_['ver']]
        cc=[]
        for pid2,pp in ALLP.items():
            if pid2==p['pid'] or pid2 in routepids or kind not in pp['kinds']: continue
            cc.append(((fees_all.get(pid2) if fees_all.get(pid2) is not None else 60)//20*20,km2(p,pp),pid2))
        cc.sort()
        glist.append({'kind':raw.get(kind) or kind,'steps':steps,'alts':[{'pid':x[2],'addr':ALLP[x[2]]['addr'],'hood':ALLP[x[2]]['hood'],'fee':fees_all.get(x[2])} for x in cc[:2]]})
    skip=[]
    for (t,v),kinds in SITES.items():
        if t in used_items or t not in REC or not (set(kinds)&here) or v not in REC[t]: continue
        hit=[x for x,qq in v if x in scarce]
        if hit and not any(have[x]<qq for x,qq in v): skip.append({'item':t,'ver':[[x,qq] for x,qq in v],'burns':sorted(set(hit))})
    skip.sort(key=lambda z:-len(z['burns']))
    bon={t:[raw.get(k) or k for k in sorted(ks&here)] for t,ks in bonus.items() if ks&here}
    usedn=set(groups.keys()); cand=[]
    for pid2,pp in ALLP.items():
        if pid2==p['pid'] or pid2 in routepids: continue
        cov=usedn&pp['kinds']
        if cov: cand.append((-len(cov),(fees_all.get(pid2) if fees_all.get(pid2) is not None else 60),km2(p,pp),pid2,cov))
    cand.sort()
    alts=[{'pid':pid2,'addr':ALLP[pid2]['addr'],'hood':ALLP[pid2]['hood'],'fee':fees_all.get(pid2),'covers':sorted(raw.get(k) or k for k in cov),'full':len(cov)==len(usedn)} for _,_,_,pid2,cov in cand[:2]]
    out.append({'delta':delta,'nstruct':len(p['raw']),'alts':alts,'again':p['pid'] in seen_pid,'n':si_out,'pid':p['pid'],'addr':p['addr'],'hood':p['hood'],'own':p['pid']==OWN,'fee':0 if p['pid']==OWN else fees_all.get(p['pid']),'kinds':p['raw'],'used':[g['kind'] for g in glist],'groups':glist,'skip':skip[:6],'bonus':bon,'lat':p['lat'],'lng':p['lng']})
for o_ in out: pass
# 4) merge crafts within each stop: dependency-aware, batch same item, stay at a structure
nb=na=0
for stop in out:
    start={d[0]:d[1] for d in stop['delta']}; units=[]
    for g in stop['groups']:
        for s in g['steps']:
            nb+=1
            for _ in range(s['count']): units.append([g['kind'],s['item'],tuple((x,qq) for x,qq,_ in s['ver']),s,s['purpose'],g])
    st2=collections.Counter(start); order=[]; left=units[:]; last=None
    ok=lambda u: all(st2[x]>=qq for x,qq in u[2])
    while left:
        kinds=collections.Counter(u[0] for u in left if ok(u)); assert kinds,('stuck',stop['n'])
        k=last if last in kinds else max(kinds,key=lambda z:kinds[z]); last=k
        while True:
            cand=[u for u in left if u[0]==k and ok(u)]
            if not cand: break
            key=(cand[0][1],cand[0][2])
            while True:
                c=[u for u in left if u[0]==k and (u[1],u[2])==key and ok(u)]
                if not c: break
                u=c[0]
                for x,qq in u[2]: st2[x]-=qq
                st2[u[1]]+=1; left.remove(u); order.append(u)
    st2=collections.Counter(start); groups=[]
    import copy
    for u in order:
        kind,item,ver,proto,pur,g=u
        if not groups or groups[-1]['kind']!=kind: groups.append({'kind':kind,'steps':[],'alts':g['alts']})
        steps=groups[-1]['steps']
        if steps and steps[-1]['item']==item and tuple((x,qq) for x,qq,_ in steps[-1]['ver'])==ver:
            s=steps[-1]; s['count']+=1
            if pur not in s['purposes']: s['purposes'].append(pur)
        else:
            s=copy.deepcopy(proto); s['count']=1; s['purposes']=[pur]; s['purpose']=pur; s['hold']=st2[item]; s['ver']=[[x,qq,st2[x]] for x,qq in ver]; steps.append(s)
        for x,qq in ver: st2[x]-=qq
        st2[item]+=1
    for g in groups:
        for s in g['steps']: s['need']=[[x,qq*s['count'],h] for x,qq,h in s['ver']]; na+=1
    stop['groups']=groups; stop['used']=[g['kind'] for g in groups]
    for d in stop['delta']: assert st2[d[0]]==d[2],(stop['n'],d)
print('cards',nb,'->',na)
# 5) meta
a=json.load(open(ROOT+'data/troves/rockdrigo/2026-11-16.json')) if False else None
final_stock=[[x,STOCK.get(x,0),have[x]] for x in sorted(set(consumed)|set(crafted_total)|targets_set) if STOCK.get(x,0)!=have[x]]
fin=collections.Counter(have)
for t in TARGETS: fin[t]-=1
FOUND=set(i[0] for i in bal['items'])
nxt=[]
for t in [t for t in REC if t not in FOUND and t not in targets_set]:
    s2=collections.Counter(fin); m,c=pl(t,1,s2,8,())
    if c and sum(m.values())<=60: nxt.append({'t':t,'crafts':len(c),'miss':dict(m),'n':sum(m.values())})
nxt.sort(key=lambda x:(x['n'],x['crafts']))
tight=sorted([(x,STOCK[x],fin[x]) for x in consumed if STOCK.get(x,0)>0 and fin[x]<=3 and x not in crafted_total],key=lambda z:z[2])
meta={'city':CITYNAME,'final':final_stock,'stops':len(out),'crafts':len(PLAN),'fees':sum((s['fee'] or 0) for s in out),'unlocked':[{'t':t,'stop':n} for t,n in unlocked],'banked':[],'scarce':sorted(scarce),'stock':dict(STOCK),'assumed':ASSUMED,'next':nxt[:6],'val':{'tight':tight[:10],'total':len(bal['items'])}}
json.dump({'meta':meta,'stops':out},open(OUTJSON,'w'))
print(len(out),'stops',len(PLAN),'crafts',meta['fees'],'UPX | unlocked',unlocked)
for s in out: print(s['n'],s['addr'],s['hood'],'fee',s['fee'],'structs',s['nstruct'],[(g['kind'][:14],[(x['count'],x['item']) for x in g['steps']]) for g in s['groups']])
print('assumed',ASSUMED,'next',[(x['t'],x['n']) for x in nxt[:5]])
