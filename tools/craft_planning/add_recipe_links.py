"""Adds direct recipe links to a craft session's data: https://play.upland.me/nft/structures/<id>/structure/recipe

  python3 add_recipe_links.py data.json

For every stop and every fallback property it reads the property's record from Upland's public API, finds the building of each
structure kind it is used for, and stores the building's nft id. stop['links'] = {kind: url}; each fallback gets 'links' the same way.
Properties are read at most 5 times a second; nothing is sent to Upland except the property ids.
"""
import json,re,sys,time,urllib.request
API='https://api.prod.upland.me/api/properties/'
norm=lambda s: re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
cache={}
def prop(pid):
    if pid in cache: return cache[pid]
    time.sleep(0.2); b=None
    for _ in range(3):
        try:
            r=urllib.request.urlopen(urllib.request.Request(API+str(pid),headers={'User-Agent':'Mozilla/5.0 (upland-tools craft links)'}),timeout=20)
            b=json.load(r).get('buildings') or []; break
        except Exception: time.sleep(1.5)
    cache[pid]=b; return b
def link(pid,kind):
    for b in prop(pid) or []:
        if norm(b.get('buildingName'))==norm(kind) and b.get('constructionStatus')=='completed' and b.get('nftID'):
            return 'https://play.upland.me/nft/structures/%s/structure/recipe'%b['nftID']
    return None
d=json.load(open(sys.argv[1])); n=miss=0
for s in d['stops']:
    kinds=[g['kind'] for g in s['groups']]
    s['links']={k:link(s['pid'],k) for k in kinds}
    for a in s.get('alts',[]): a['links']={k:link(a['pid'],k) for k in a.get('covers',kinds)}
    for g in s['groups']:
        for a in g.get('alts',[]): a['links']={g['kind']:link(a['pid'],g['kind'])}
    for L in [s['links']]+[a['links'] for a in s.get('alts',[])]+[a['links'] for g in s['groups'] for a in g.get('alts',[])]:
        for v in L.values():
            n+=1; miss+=v is None
json.dump(d,open(sys.argv[1],'w'))
print(n,'links,',miss,'not found')
