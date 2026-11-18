import json,re,collections,math,glob,random,time,copy
ROOT='/Users/rock/code/upland-tools/'
def norm(s): return re.sub(r' 1$','',re.sub(r'[^a-z0-9]+',' ',s.lower()).strip())
bal=json.load(open(ROOT+'data/troves/rockdrigo/latest.json'))
STOCK=collections.Counter({i[0]:i[2] for i in bal['items']}); FOUND=set(STOCK)
REC=collections.defaultdict(list)
for a,ing in bal['recipes']: REC[a].append(tuple(sorted((x,q) for x,q in ing)))
cs=json.load(open(ROOT+'data/troves/craft-sites.json'))['troves']; sr=json.load(open(ROOT+'data/troves/structure-recipes.json'))['structures']
SITES=collections.defaultdict(dict)
for t,v in cs.items():
    for ver in v['versions']:
        for a in ver['at']: SITES[(t,tuple(sorted((x,qq) for x,qq in ver['ing'])))].setdefault(norm(a),'upxland')
for f in glob.glob('/Users/rock/Downloads/trove-hunting-session-2026-11-1*.json'):
    for c in json.load(open(f))['crafts']: SITES[(c['recipe'],tuple(sorted((x,qq) for x,qq in c['ingredients'])))][norm(c['building'])]='seen'
for b,d in sr.items():
    for t,names in d.items():
        for v in REC.get(t,[]):
            if sorted(x for x,_ in v)==sorted(names): SITES[(t,v)][norm(b)]='seen'
QW=json.load(open(ROOT+'data/structures/map/quailwood.json'))
fees0=json.load(open(ROOT+'data/troves/fees.json'))['fees']
sites_all={k for v in SITES.values() for k in v}
props={}
for r in QW['rows']:
    ks={norm(b[0]) for b in r[7]}&sites_all
    if not ks: continue
    props[r[0]]={'pid':r[0],'addr':r[1],'lat':r[3],'lng':r[4],'owner':r[5],'mine':r[5]=='rockdrigo','kinds':ks,'raw':sorted({b[0] for b in r[7] if norm(b[0]) in sites_all}),'hood':'QUAILWOOD','fee':0 if r[5]=='rockdrigo' else fees0.get(r[0])}
QK={k for p in props.values() for k in p['kinds']}
print('craft properties',len(props),'mine',sum(1 for p in props.values() if p['mine']))
def qsites(t,v):
    if t=='Compass' and any(x=='Binoculars' for x,_ in v): return {}
    return {k:e for k,e in SITES.get((t,v),{}).items() if k in QK}
def kinds_of(item,v): return set(qsites(item,v))
def pl(item,n,stock,depth,path,out,miss):
    have=min(stock[item],n); stock[item]-=have; need=n-have
    while need>0:
        if item not in REC or item in path or depth<=0: miss[item]+=need; return
        best=None
        for v in REC[item]:
            if not qsites(item,v): continue
            st=collections.Counter(stock); m=collections.Counter(); cr=[]
            for x,qq in v: pl(x,qq,st,depth-1,path+(item,),cr,m)
            sc=(sum(m.values()),len(cr))
            if best is None or sc<best[0]: best=(sc,m,cr,st,v)
        if best is None: miss[item]+=need; return
        _,m,cr,st,v=best; stock.clear(); stock.update(st); miss.update(m); out+=cr+[(item,v)]; need-=1
TARGETS=['Sunday Dinner','Plasma Cutter','Emerald','Lifeline','Soulmate','Amber','Bread Mother','Cloud Nine','Tesla Coil','Hourglass']
st=collections.Counter(STOCK); raw_plan=[]; MISS=collections.Counter()
for t in TARGETS:
    c=[]; pl(t,1,st,8,(),c,MISS); raw_plan+=[(i,v,'unlock '+t) for i,v in c]
# keep only the crafts that can really be done, in dependency order (a craft needs its ingredients made earlier)
av=collections.Counter(STOCK); PLAN=[]; pend=list(raw_plan); prog=True
while prog:
    prog=False
    for c in list(pend):
        it,v,pu=c
        if all(av[x]>=qq for x,qq in v):
            for x,qq in v: av[x]-=qq
            av[it]+=1; PLAN.append(c); pend.remove(c); prog=True
dropped=collections.Counter(it for it,_,_ in pend)
print('planned',len(raw_plan),'doable',len(PLAN),'dropped',sum(dropped.values()),'missing raw',dict(MISS))
# remove crafts that produce items nobody consumes and that are not a target (should not exist, but keep honest)
made=collections.Counter(it for it,_,_ in PLAN)
# 2) route: your properties first, then others by cost
need_kinds=[kinds_of(it,v) for it,v,_ in PLAN]
def rest_ok(a0,rest):
    a=collections.Counter(a0)
    for j in rest:
        for x,qq in PLAN[j][1]:
            if a[x]<qq: return False
            a[x]-=qq
        a[PLAN[j][0]]+=1
    return True
def sched(order):
    a=collections.Counter(STOCK); todo=list(range(len(PLAN))); used=[]; sc={}
    for si,p in enumerate(order):
        n=0; ch=True
        while ch:
            ch=False
            for i in list(todo):
                it,v,pu=PLAN[i]; ks=need_kinds[i]&p['kinds']
                if ks and all(a[x]>=qq for x,qq in v):
                    a2=collections.Counter(a)
                    for x,qq in v: a2[x]-=qq
                    a2[it]+=1
                    if not rest_ok(a2,[j for j in todo if j!=i]): continue
                    a=a2; todo.remove(i); n+=1; ch=True; sc.setdefault(si,[]).append((i,sorted(ks)[0]))
        if n: used.append(p)
    return todo,used,sc,a
mine=[p for p in props.values() if p['mine']]; others=[p for p in props.values() if not p['mine']]
# which of mine are useful at all
mine=[p for p in mine if any(need_kinds[i]&p['kinds'] for i in range(len(PLAN)))]
covered=set(i for i in range(len(PLAN)) if any(need_kinds[i]&p['kinds'] for p in mine))
unc=[i for i in range(len(PLAN)) if i not in covered]
pick=[]
while unc:
    best=None
    for p in others:
        g=sum(1 for i in unc if need_kinds[i]&p['kinds'])
        if not g: continue
        s=g/(10+(p['fee'] if p['fee'] is not None else 15)+len(p['kinds'])*0.3)
        if best is None or s>best[0]: best=(s,p)
    if best is None: print('NO SITE for',[PLAN[i][0] for i in unc]); break
    pick.append(best[1]); unc=[i for i in unc if not (need_kinds[i]&best[1]['kinds'])]
print('mine useful',len(mine),'others picked',len(pick))
def cost(order):
    todo,used,_,_=sched(order)
    return (len(todo),sum(p['fee'] or 15 for p in used),len(used))
random.seed(11); best=None; t0=time.time()
while time.time()-t0<50:
    m=mine[:]; o=pick[:]; random.shuffle(m); random.shuffle(o)
    c=cost(m+o)
    if best is None or c<best[0]: best=(c,m,o)
(cur_m,cur_o)=(best[1],best[2]); curc=best[0]; t1=time.time()
while time.time()-t1<60:
    m=cur_m[:]; o=cur_o[:]
    L=m if (random.random()<.5 and len(m)>1) else o
    if len(L)<2: continue
    i=random.randrange(len(L)); p=L.pop(i); L.insert(random.randrange(len(L)+1),p)
    c=cost(m+o)
    if c<=curc: cur_m,cur_o,curc=m,o,c
route=cur_m+cur_o; print('order cost',curc)
todo,used,sc,final_av=sched(route)
extra=0
while todo and extra<10:
    extra+=1; bp=None
    for allow in (False,True):
        for p in props.values():
            if (p in route) and not allow: continue
            g=sum(1 for i in todo if need_kinds[i]&p['kinds'])
            if not g: continue
            s=g/(10+(p['fee'] if p['fee'] is not None else 15))
            if bp is None or s>bp[0]: bp=(s,p)
        if bp: break
    if not bp: break
    route.append(dict(bp[1]) if bp[1] in route else bp[1]); todo,used,sc,final_av=sched(route)
print('unscheduled',[PLAN[i][0] for i in todo],'stops',len(used))
# 3) stop data
need_set=set(); stack=[t for t in REC if t not in FOUND]
while stack:
    t=stack.pop()
    for v in REC.get(t,[]):
        for x,_ in v:
            if x not in need_set: need_set.add(x); stack.append(x)
after=collections.Counter(STOCK)
for it,v,pu in PLAN:
    for x,qq in v: after[x]-=qq
    after[it]+=1
scarce={x for x in need_set if STOCK.get(x,0)>0 and after[x]<=5}
needed_later=collections.Counter()
for it,v,pu in raw_plan:
    for x,qq in v: needed_later[x]+=qq
crafted_total=collections.Counter(it for it,_,_ in PLAN)
ALLP=props
raw_kind={}
for r in QW['rows']:
    for b in r[7]: raw_kind.setdefault(norm(b[0]),b[0])
have=collections.Counter(STOCK); out=[]; seen_pid=set(); si_out=0
routepids={p['pid'] for p in route}
for si,p in enumerate(route):
    if si not in sc: continue
    si_out+=1; here=p['kinds']; before=collections.Counter(have); groups=collections.OrderedDict(); used_items=set()
    for i,kind in sc[si]:
        item,ver,pu=PLAN[i]; ev=SITES[(item,ver)].get(kind,'upxland'); used_items.add(item)
        g=groups.setdefault(kind,[])
        alts=[{'ver':[[x,qq] for x,qq in v2],'warn':[x for x,qq in v2 if x in scarce or STOCK.get(x,0)<qq]} for v2 in REC.get(item,[]) if v2!=ver]
        g.append({'hold':have[item],'plan_needs':needed_later[item],'plan_makes':crafted_total[item],'item':item,'ver':[[x,qq,have[x]] for x,qq in ver],'count':1,'purpose':pu,'evidence':ev,'alts':alts})
        for x,qq in ver: have[x]-=qq
        have[item]+=1
    touched=sorted({x for g_ in groups.values() for s_ in g_ for x,_,_ in s_['ver']}|{s_['item'] for g_ in groups.values() for s_ in g_})
    delta=[[x,before[x],have[x]] for x in touched]
    glist=[]
    for kind,steps in groups.items():
        cc=sorted(((pp['fee'] if pp['fee'] is not None else 15),pid2) for pid2,pp in props.items() if pid2!=p['pid'] and pid2 not in routepids and kind in pp['kinds'])
        glist.append({'kind':raw_kind.get(kind) or kind,'steps':steps,'alts':[{'pid':x[1],'addr':props[x[1]]['addr'],'hood':'QUAILWOOD','fee':props[x[1]]['fee'],'owner':props[x[1]]['owner']} for x in cc[:2]]})
    skip=[]
    for (t,v),kinds in SITES.items():
        if t in used_items or t not in REC or not (set(kinds)&here) or v not in REC[t]: continue
        hit=[x for x,qq in v if x in scarce]
        if hit and not any(have[x]<qq for x,qq in v): skip.append({'item':t,'ver':[[x,qq] for x,qq in v],'burns':sorted(set(hit))})
    skip.sort(key=lambda z:-len(z['burns']))
    usedn=set(groups.keys()); cand=[]
    for pid2,pp in props.items():
        if pid2==p['pid'] or pid2 in routepids: continue
        cov=usedn&pp['kinds']
        if cov: cand.append((-len(cov),(pp['fee'] if pp['fee'] is not None else 15),pid2,cov))
    cand.sort()
    alts=[{'pid':x[2],'addr':props[x[2]]['addr'],'hood':'QUAILWOOD','fee':props[x[2]]['fee'],'owner':props[x[2]]['owner'],'covers':sorted(raw_kind.get(k) or k for k in x[3]),'full':len(x[3])==len(usedn)} for x in cand[:2]]
    out.append({'delta':delta,'nstruct':len(p['raw']),'alts':alts,'again':p['pid'] in seen_pid,'n':si_out,'pid':p['pid'],'addr':p['addr'],'hood':'QUAILWOOD','owner':p['owner'],'own':p['mine'],'fee':p['fee'],'kinds':p['raw'],'used':[g['kind'] for g in glist],'groups':glist,'skip':skip[:6],'bonus':{},'lat':p['lat'],'lng':p['lng']}); seen_pid.add(p['pid'])
# 4) merge crafts inside a stop
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
# 5) meta
tgt_crafts=collections.Counter(pu[7:] for _,_,pu in PLAN)
final_stock=[[x,STOCK.get(x,0),have[x]] for x in sorted(set(STOCK)|set(have)) if STOCK.get(x,0)!=have[x]]
made_items=collections.Counter(it for it,_,_ in PLAN)
meta={'final':final_stock,'stops':len(out),'crafts':len(PLAN),'fees':sum((s['fee'] or 0) for s in out),'unlocked':[],'banked':[],'scarce':sorted(scarce),'assumed':{},'city':'Bakersfield, CA','buildup':[{'t':t,'crafts':n} for t,n in tgt_crafts.most_common()],'made':[[k,v] for k,v in made_items.most_common()],'missing':dict(MISS),'dropped':sum(dropped.values()),'mine_stops':sum(1 for s in out if s['own']),'next':[],'val':{'tight':sorted([(x,STOCK[x],have[x]) for x in STOCK if STOCK[x]>0 and have[x]<=2 and STOCK[x]!=have[x]],key=lambda z:z[2])[:10],'total':len(bal['items'])}}
json.dump({'meta':meta,'stops':out},open('s9/qdata.json','w'))
print('cards',nb,'->',na,'|',len(out),'stops (',meta['mine_stops'],'yours )',len(PLAN),'crafts, fees',meta['fees'])
for s in out: print(s['n'],'YOURS' if s['own'] else s['owner'],s['addr'],'fee',s['fee'],sum(x['count'] for g in s['groups'] for x in g['steps']),'crafts')
print(meta['buildup']); print('made',made_items.most_common(12))
