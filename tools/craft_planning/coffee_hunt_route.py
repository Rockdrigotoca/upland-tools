import json,math,re,sys,os
ROOT='/Users/rock/code/upland-tools/';D=ROOT+'data/'
def norm(s): return re.sub(r' 1$','',re.sub(r'[^a-z0-9]+',' ',s.lower()).strip())
def rw(d):
    if d<=60: return 1.0
    if d>=100: return 0.0
    pts=[(60,1.0),(70,.63),(80,.46),(90,.3),(100,0.0)]
    for (d0,w0),(d1,w1) in zip(pts,pts[1:]):
        if d<=d1: return w0+(w1-w0)*(d-d0)/(d1-d0)
places=json.load(open(D+'troves/places.json')); fees=json.load(open(D+'troves/fees.json'))['fees']
best=json.load(open(D+'troves/reach-best.json'))['best80']
hh=json.load(open(D+'troves/rockdrigo/hunts.json'))
emp={};evn={}
for f in hh['finds']:
    if f[1]!=0: continue
    k=norm(hh['src'][f[2]][0]); evn[k]=evn.get(k,0)+1
    e=emp.setdefault(k,{}); tn=hh['troves'][f[3]]; e[tn]=e.get(tn,0)+f[4]
kind={}
for r in places['troves']:
    for s in r[2]: kind.setdefault(norm(s),set()).add(r[0])
def prob(k,ln): 
    n=evn.get(k,0); return (emp.get(k,{}).get('Coffee Bean',0)+4.0/ln)/(n+4.0)
M=111320.0

def build(cid,tag,maxn=120,need=10):
    cd=json.load(open(D+'troves/places/%s.json'%cid)); sn=[norm(x) for x in cd['structs']]
    try: own=json.load(open(D+'helper/own/rockdrigo/%s.json'%cid))['stops']
    except Exception: own={}
    rows=[{'pid':str(p[0]),'addr':p[1],'lat':p[2],'lng':p[3],'ks':[sn[k] for k in p[5] if sn[k] in kind],'hood':cd['hoods'][p[4]]} for p in cd['props']]
    rows=[x for x in rows if x['ks']]
    r=100/M; grid={}
    cell=lambda x:(math.floor(x['lat']/r),math.floor(x['lng']/(r/max(math.cos(math.radians(x['lat'])),.2))))
    for x in rows: grid.setdefault(cell(x),[]).append(x)
    cand=[]
    for x in rows:
        cy,cx=cell(x); ch=0
        for dy in(-1,0,1):
            for dx in(-1,0,1):
                for o in grid.get((cy+dy,cx+dx),[]):
                    d=0 if o is x else math.hypot((o['lat']-x['lat'])*M,(o['lng']-x['lng'])*M*math.cos(math.radians(x['lat'])))
                    w=rw(d)
                    if w<=0: continue
                    for k in o['ks']:
                        if 'Coffee Bean' in kind[k]: ch=1-(1-ch)*(1-w*prob(k,len(kind[k])))
        if ch<=0: continue
        b=best.get(x['pid']); x['stand'],x['fee']=(str(b[0]),b[1]) if b else (x['pid'],fees.get(x['pid']))
        o=own.get(x['pid']); x['own']=o if o and o[2]<=150 else None
        x['key']=x['own'][0] if x['own'] else x['stand']; x['ch']=ch; cand.append(x)
    left=float(need); used=set(); picked=[]
    while cand and len(picked)<maxn:
        def sc(x): return x['ch']/(1+(0 if x['own'] else (x['fee'] if x['fee'] is not None else 50))/100)
        x=max(cand,key=sc)
        picked.append(x); used.add(x['key']); cand=[y for y in cand if y['key']!=x['key']]
    n=(len(picked)+39)//40; out=os.path.expanduser('~/Downloads')
    for k in range(n):
        ch=picked[k*40:(k+1)*40]; name='%s_part%d_of_%d.csv'%(tag,k+1,n)
        with open(os.path.join(out,name),'w',encoding='utf-8',newline='') as f:
            f.write('name,property_id,city_id,order\n')
            for i,x in enumerate(ch,1):
                hit='Coffee %d%%'%round(100*x['ch'])
                if x['own']: label,pid='%s (own, free) -> ~%s m to %s [%s]'%(x['own'][1],x['own'][2],x['addr'],hit),x['own'][0]
                else: label,pid='%s (fee %s) [%s]'%(x['addr'],x['fee'] if x['fee'] is not None else '?',hit),x['stand']
                f.write('"'+label.replace('"',"'")+'",%s,%s,%d\n'%(pid,cid,i))
        print(name,len(ch),'rows, expected',round(sum(x['ch'] for x in ch),2),'fees',sum(0 if x['own'] else (x['fee'] or 0) for x in ch),'free',sum(1 for x in ch if x['own']))
    print('total',len(picked),'distinct keys',len({x['key'] for x in picked}))
build(32,'LA_coffee_hunt')
