import sys, json, collections, statistics as st, random, math
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'pipeline'))
from statsbomb import *
import numpy as np, pandas as pd
AM=1229
rows=[]; ms=[]
for sid,sn in SEASONS.items():
    for m in matches(sid):
        h,a=m['home_team'],m['away_team']
        if AM not in (h['home_team_id'],a['away_team_id']) or m['match_status_360']!='available': continue
        home = h['home_team_id']==AM
        me = h if home else a
        mg=', '.join(x.get('nickname') or x['name'] for x in (me.get('managers') or [])) or '?'
        ms.append(dict(mid=m['match_id'],date=m['match_date'],season=sn,home=home,opp=(a['away_team_name'] if home else h['home_team_name']),
           gf=m['home_score'] if home else m['away_score'],ga=m['away_score'] if home else m['home_score'],
           stage=m['competition_stage']['name'],coach=mg))
M=pd.DataFrame(ms)
M['torneo']=np.where(pd.to_datetime(M.date).dt.month>=7,'Apertura','Clausura')
M['liguilla']=~M.stage.isin(['Regular Season','Apertura','Clausura'])
print(M.groupby('coach').size())
def ev(mid):
    f=CACHE/f'v8_events_{mid}.json'
    return json.load(open(f)) if f.exists() else None
out=[]; pos=collections.defaultdict(lambda: collections.defaultdict(list)); forms=collections.Counter()
sim=[]
for r in M.itertuples():
    E=ev(r.mid)
    if E is None: continue
    # score state timeline
    goals=[]
    for e in E:
        t=e['type']['name']
        if (t=='Shot' and e['shot']['outcome']['name']=='Goal') or t=='Own Goal For':
            goals.append((e['period'],e['minute'],e['second'],1 if e['team']['id']==AM else -1, e['index']))
    goals.sort(key=lambda g:g[4])
    def state(e):
        d=sum(g[3] for g in goals if g[4]<e['index'])
        return 'Ganando' if d>0 else ('Perdiendo' if d<0 else 'Empatando')
    agg=collections.defaultdict(lambda: collections.Counter())
    for e in E:
        if e['period']>4: continue
        s=state(e); t=e['type']['name']; mine=e['team']['id']==AM; A=agg[s]
        if t=='Pass' and 'outcome' not in e['pass'] or (t=='Pass' and e['pass'].get('outcome',{}).get('name') is None):
            pass
        if t=='Pass':
            ok='outcome' not in e['pass']
            if mine:
                A['p']+=1; A['pok']+=ok
                if e['pass']['length']>32 : A['long']+=1
                dx=e['pass']['end_location'][0]-e['location'][0]; A['fwd']+=dx>10
            else:
                A['op']+=1
                if e['location'][0]<72: A['op_own']+=1   # opponent passes in their 60% (PPDA denominator style)
        if mine and t in ('Pressure','Duel','Interception','Foul Committed','Ball Recovery','Block','Clearance'):
            A['def']+=1; A['defx']+=e['location'][0] if 'location' in e else 0
            if e['location'][0]>=48 and (t in ('Interception','Foul Committed') or (t=='Duel' and e['duel']['type']['name']=='Tackle')): A['ppda_def']+=1
        if t=='Shot' and e['shot']['type']['name']!='Penalty':
            A['xg' if mine else 'xga']+=e['shot']['statsbomb_xg']
        A['sec']+= 0
    # minutes per state approx via event timestamps
    last=None
    for e in E:
        if e['period']>4: continue
        tsec=e['minute']*60+e['second']
        if last and last[0]==e['period']: agg[state(e)]['secs']+=max(0,tsec-last[1])
        last=(e['period'],tsec)
    for s,A in agg.items(): out.append(dict(mid=r.mid,coach=r.coach,state=s,**A))
    # formations & avg positions (starting XI, in poss vs out)
    for e in E:
        if e['type']['name']=='Starting XI' and e['team']['id']==AM: forms[(r.coach,e['tactics']['formation'])]+=1
        if e['team']['id']==AM and 'location' in e and 'position' in e and e['period']<=2:
            k='con' if e['possession_team']['id']==AM else 'sin'
            pos[(r.coach,k)][e['position']['name']].append(e['location'])
    # xG simulation
    xs={True:[],False:[]}
    for e in E:
        if e['type']['name']=='Shot' and e['period']<=4: xs[e['team']['id']==AM].append(e['shot']['statsbomb_xg'])
    W=D=L=0; rng=np.random.default_rng(r.mid)
    for _ in range(5000):
        g1=(rng.random(len(xs[True]))<np.array(xs[True])).sum(); g2=(rng.random(len(xs[False]))<np.array(xs[False])).sum()
        W+=g1>g2; D+=g1==g2; L+=g1<g2
    sim.append(dict(mid=r.mid,coach=r.coach,xp=(3*W+D)/5000,pts=3*(r.gf>r.ga)+(r.gf==r.ga),pW=W/5000,xg=sum(xs[True]),xga=sum(xs[False]),gf=r.gf,ga=r.ga,opp=r.opp,date=r.date,liguilla=r.liguilla))
S=pd.DataFrame(out).fillna(0)
g=S.groupby(['coach','state']).sum(numeric_only=True)
g['min']=g.secs/60; g['pass_share']=g.p/(g.p+g.op); g['long%']=g.long/g.p; g['fwd%']=g.fwd/g.p
g['PPDA']=g.op_own/g.ppda_def; g['def_height']=g.defx/g['def']; g['xg90']=g.xg/g['min']*90; g['xga90']=g.xga/g['min']*90
print(g[['min','pass_share','long%','fwd%','PPDA','def_height','xg90','xga90']].round(3).to_string())
print(sorted(forms.items(),key=lambda x:-x[1])[:12])
SIM=pd.DataFrame(sim); print(SIM.groupby('coach')[['xp','pts','xg','xga']].mean().round(2)); print(SIM.groupby(['coach','liguilla'])[['xp','pts','xg','xga']].mean().round(2))
SIM.to_csv('data/out/sim.csv',index=False)
g.reset_index().to_csv('data/out/state.csv',index=False)
P={f'{c}|{k}':{p:[round(float(np.mean([l[0] for l in v])),1),round(float(np.mean([l[1] for l in v])),1),len(v)] for p,v in d.items() if len(v)>300} for (c,k),d in pos.items()}
json.dump(P,open('data/out/avgpos.json','w'))

# ---- 360: opponents bypassed per completed pass (packing-like), Jardine vs others; + players behind ball at turnover
SC='data/out/'
pk=collections.defaultdict(list); behind=collections.defaultdict(list)
for r in M.itertuples():
    E=ev(r.mid); f=CACHE/f'v2_360-frames_{r.mid}.json'
    if E is None or not f.exists(): continue
    FR={x['event_uuid']:x['freeze_frame'] for x in json.load(open(f))}
    for e in E:
        if e['type']['name']!='Pass' or e['team']['id']!=AM or 'outcome' in e['pass'] or e['id'] not in FR: continue
        x0=e['location'][0]; x1=e['pass']['end_location'][0]
        if x1<=x0: pk[r.coach].append(0); continue
        pk[r.coach].append(sum(1 for p in FR[e['id']] if not p['teammate'] and not p['keeper'] and x0<p['location'][0]<x1))
    # when opponent recovers (Ball Recovery / Interception by opp), count AM players visible goal-side of ball (in opp frame: AM are non-teammates with x > ball x)
    for e in E:
        if e['team']['id']==AM or e['type']['name'] not in ('Ball Recovery','Interception') or e['id'] not in FR: continue
        bx=e['location'][0]
        behind[r.coach].append(sum(1 for p in FR[e['id']] if not p['teammate'] and not p['keeper'] and p['location'][0]>bx))
print('opponents bypassed / completed pass:',{k:round(np.mean(v),3) for k,v in pk.items()})
print('% passes bypassing >=3:',{k:round(np.mean(np.array(v)>=3),3) for k,v in pk.items()})
print('AM outfield players goal-side at opp recovery (visible):',{k:round(np.mean(v),2) for k,v in behind.items()})
# opponent strength split: opponent season xGD/game rank
L=pd.DataFrame([x for sid in SEASONS for x in get(f'v2/competitions/73/seasons/{sid}/team-stats')])
L['rk']=L.groupby('season_id').team_season_xgd_pg.rank(ascending=False)
top={(r.season_name,r.team_name) for r in L.itertuples() if r.rk<=6}
SIM['season']=SIM.mid.map(dict(zip(M.mid,M.season)))
SIM['top6']=[ (s.replace('/','/20') if False else s, o) for s,o in zip(SIM.season,SIM.opp)]
sn={108:'2021/2022',235:'2022/2023',281:'2023/2024',317:'2024/2025',318:'2025/2026',351:'2026/2027'}
inv={v:k for k,v in SEASONS.items()}
SIM['top6']=[(sn[inv[s]],o) in top for s,o in zip(SIM.season,SIM.opp)]
print(SIM[SIM.coach=='André Jardine'].groupby(['liguilla','top6'])[['xp','pts','xg','xga']].agg(['mean','count']).round(2))
