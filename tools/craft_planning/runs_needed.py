import json,collections,sys,datetime
exec(open('/private/tmp/claude-501/-Users-rock-code-upland-tools/e3ad70ac-2ff2-4024-9d9b-cbf94f6140ea/scratchpad/s8/left.py').read().split("und=sorted")[0])
und=sorted(t for t in REC if t not in FOUND)
KNOWN_NOSITE={'Golden Record','Invisible Cloak','Jade Dragon','Meteorite','Skeleton Key'}
cand=[t for t in und if t not in KNOWN_NOSITE]
# yield per 100 sends since the lap sessions (11-16 03:19 onward)
h=json.load(open(ROOT+'data/troves/rockdrigo/hunts.json')); r=json.load(open(ROOT+'data/troves/rockdrigo/rounds.json'))
T0=int(datetime.datetime(2026,11,16,3,19,tzinfo=datetime.timezone.utc).timestamp())
sends=[s for s in r['sends'] if s[0]>=T0]; ns=len(sends); fee=sum(f for _,f in sends)
y=collections.Counter(); 
for f in h['finds']:
    if f[0]>=T0: y[h['troves'][f[3]]]+=f[4]
print('since 11-16 03:19:',ns,'sends,',fee,'UPX,',sum(y.values()),'units')
perrun={k:v/ns*100 for k,v in y.items()}   # per 100 sends
# queens-only huntable?
cityq=collections.Counter()
for f in h['finds']:
    if h['cities'][h['props'][f[5]][2]]=='Queens': cityq[h['troves'][f[3]]]+=f[4]
def need_for(set_):
    st=collections.Counter(STOCK); miss=collections.Counter(); cr=0
    for t in set_:
        m,c=pl(t,1,st,8,()); miss+=m; cr+=len(c)
    return miss,cr
def runs(miss):
    rows=[]
    for k,q in miss.items():
        pr=perrun.get(k,0)
        rows.append((q/pr if pr else float('inf'),k,q,round(pr,1),cityq.get(k,0)))
    return sorted(rows,reverse=True)
# greedy pick the next 10 by smallest added missing units (then crafts)
chosen=[]
st_set=[]
for _ in range(10):
    best=None
    for t in cand:
        if t in chosen: continue
        m,c=need_for(chosen+[t]); sc=(sum(m.values()),c)
        if best is None or sc<best[0]: best=(sc,t,m,c)
    chosen.append(best[1]); print(len(chosen),best[1],'cum missing',sum(best[2].values()),'crafts',best[3])
m,c=need_for(chosen); print('NEXT 10',chosen,'crafts',c,'missing',dict(m))
for x in runs(m): print('  ',x)
print('--- ALL known craftable (36 minus no-site 5)')
m2,c2=need_for(cand); print('crafts',c2,'missing units',sum(m2.values()))
for x in runs(m2)[:14]: print('  ',x)
