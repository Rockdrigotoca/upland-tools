import json,math,re,glob,collections,os
ROOT='/Users/rock/code/upland-tools/';D=ROOT+'data/'
def norm(s): return re.sub(r' 1$','',re.sub(r'[^a-z0-9]+',' ',s.lower()).strip())
def rw(d):
    if d<=60: return 1.0
    if d>=100: return 0.0
    pts=[(60,1.0),(70,.63),(80,.46),(90,.3),(100,0.0)]
    for (d0,w0),(d1,w1) in zip(pts,pts[1:]):
        if d<=d1: return w0+(w1-w0)*(d-d0)/(d1-d0)
import sys
CID=int(sys.argv[1]); TAG=sys.argv[2]; NEED=json.loads(sys.argv[3]); NFILES=int(sys.argv[4]) if len(sys.argv)>4 else 3
# usage: hunt_route.py <city id> <file tag> '{"Coal Lump":30,...}' [files of 40]
places=json.load(open(D+'troves/places.json')); fees=json.load(open(D+'troves/fees.json'))['fees']; best=json.load(open(D+'troves/reach-best.json'))['best80']
cd=json.load(open(D+'troves/places/%d.json'%CID+'')); sn=[norm(x) for x in cd['structs']]
own=json.load(open(D+'helper/own/rockdrigo/%d.json'%CID+''))['stops']
qprops={str(p[0]):p for p in cd['props']}
# ---- history: visits per property = bursts of hunt events on that prop (from hunts.json)
hh=json.load(open(D+'troves/rockdrigo/hunts.json'))
ev=collections.defaultdict(list)
for f in hh['finds']:
    pid=str(hh['props'][f[5]][0]); ev[pid].append((f[0],hh['troves'][f[3]],f[4]))
vis=collections.defaultdict(list)
for p,hs in ev.items():
    hs.sort(); cur=None; last=0
    for t,name,n in hs:
        if cur is None or t-last>90: cur=collections.Counter(); vis[p].append(cur)
        last=t; cur[name]+=n
# ---- model prior
emp={};evn={}
for f in hh['finds']:
    if f[1]!=0: continue
    k=norm(hh['src'][f[2]][0]); evn[k]=evn.get(k,0)+1
    e=emp.setdefault(k,{}); tn=hh['troves'][f[3]]; e[tn]=e.get(tn,0)+1
kind={}
for r in places['troves']:
    for s in r[2]: kind.setdefault(norm(s),set()).add(r[0])
def prob(k,t,ln): n=evn.get(k,0); return (emp.get(k,{}).get(t,0)+4.0/ln)/(n+4.0)
M=111320.0; r=100/M
rows=[{'pid':str(p[0]),'addr':p[1],'lat':p[2],'lng':p[3],'ks':[sn[k] for k in p[5] if sn[k] in kind],'hood':cd['hoods'][p[4]]} for p in cd['props']]
rows=[x for x in rows if x['ks'] and x['hood']!='HOWARD BEACH']
grid={}
cell=lambda x:(math.floor(x['lat']/r),math.floor(x['lng']/(r/max(math.cos(math.radians(x['lat'])),.2))))
for x in rows: grid.setdefault(cell(x),[]).append(x)
for x in rows:
    cy,cx=cell(x); ch=dict.fromkeys(NEED,0.0)
    for dy in(-1,0,1):
        for dx in(-1,0,1):
            for o in grid.get((cy+dy,cx+dx),[]):
                d=0 if o is x else math.hypot((o['lat']-x['lat'])*M,(o['lng']-x['lng'])*M*math.cos(math.radians(x['lat'])))
                w=rw(d)
                if w<=0: continue
                for k in o['ks']:
                    for t in NEED:
                        if t in kind[k]: ch[t]=1-(1-ch[t])*(1-w*prob(k,t,len(kind[k])))
    x['prior']=ch
    v=vis.get(x['pid'],[]); x['n']=len(v)
    obs=collections.Counter()
    for c in v:
        for t in NEED: obs[t]+=c.get(t,0)
    x['obs']=obs
    K=3.0
    x['exp']={t:(obs[t]+K*ch[t])/(x['n']+K) for t in NEED}
    b=best.get(x['pid']); x['stand'],x['fee']=(str(b[0]),b[1]) if b else (x['pid'],fees.get(x['pid']))
    o=own.get(x['pid']); x['own']=o if o and o[2]<=150 else None
    x['key']=x['own'][0] if x['own'] else x['stand']
# ---- validation: model vs history on visited properties
vp=[x for x in rows if x['n']>=2]
tot_obs=sum(sum(x['obs'][t]/NEED[t] for t in NEED) for x in vp); tot_pr=sum(x['n']*sum(x['prior'][t]/NEED[t] for t in NEED) for x in vp)
print('visited props (>=2 visits):',len(vp),'| observed need-weighted units',round(tot_obs,2),'vs model',round(tot_pr,2),'ratio',round(tot_obs/tot_pr,2))
for t in NEED:
    o=sum(x['obs'][t] for x in vp); m=sum(x['n']*x['prior'][t] for x in vp); print('  ',t,'observed',o,'model',round(m,1))
def val(x,left): return sum(x['exp'][t]*max(0,left[t])/NEED[t] for t in NEED)
left=dict(NEED); cand=[x for x in rows]; picked=[]; used=set()
while cand and len(picked)<40*NFILES:
    def sc(x): return val(x,left)/(1+(0 if x['own'] else (x['fee'] if x['fee'] is not None else 50))/100)
    x=max(cand,key=sc); picked.append(x)
    for t in NEED: left[t]-=x['exp'][t]
    cand=[y for y in cand if y['key']!=x['key']]
print('picked',len(picked),'| previously visited:',sum(1 for x in picked if x['n']>0),'| with >=2 visits',sum(1 for x in picked if x['n']>=2))
print('expected over 120:',{t:round(NEED[t]-left[t],1) for t in NEED})
out=os.environ.get('OUT') or os.path.expanduser('~/Downloads')
for k in range(NFILES):
    ch=picked[k*40:(k+1)*40]; name='%s_part%d_of_%d.csv'%(TAG,k+1,NFILES)
    with open(os.path.join(out,name),'w',encoding='utf-8',newline='') as f:
        f.write('name,property_id,city_id,order\n')
        for i,x in enumerate(ch,1):
            top=sorted(NEED,key=lambda t:-x['exp'][t]/NEED[t])[:3]
            hit='/'.join(top)+(' | seen %dx'%x['n'] if x['n'] else '')
            if x['own']: label,pid='%s (own, free) -> ~%s m to %s [%s]'%(x['own'][1],x['own'][2],x['addr'],hit),x['own'][0]
            else: label,pid='%s (fee %s) [%s]'%(x['addr'],x['fee'] if x['fee'] is not None else '?',hit),x['stand']
            f.write('"'+label.replace('"',"'")+'",%s,%d,%d\n'%(pid,CID,i))
    print(name,'fees',sum(0 if x['own'] else (x['fee'] or 0) for x in ch),'free',sum(1 for x in ch if x['own']),'visited before',sum(1 for x in ch if x['n']),'need-weighted',round(sum(val(x,NEED) for x in ch),2))
# best historic performers
bp=sorted([x for x in rows if x['n']>=3],key=lambda x:-sum(x['obs'][t]/NEED[t] for t in NEED)/x['n'])[:8]
for x in bp: print('  best:',x['addr'],x['hood'],'visits',x['n'],'per visit',round(sum(x['obs'][t]/NEED[t] for t in NEED)/x['n'],3),{t:x['obs'][t] for t in NEED if x['obs'][t]})
