import sys,json; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'pipeline'))
from statsbomb import *
import pandas as pd, numpy as np
L=pd.DataFrame([x for sid in SEASONS for x in get(f'v2/competitions/73/seasons/{sid}/team-stats')])
# América per coach from match-level team stats
rows=[]
for sid in SEASONS:
    for m in matches(sid):
        for side in ['home','away']:
            t=m[side+'_team']
            if t[side+'_team_id']!=1229: continue
            f=CACHE/f"v1_matches_{m['match_id']}_team-stats.json"
            if not f.exists(): continue
            ts=[x for x in json.load(open(f)) if x['team_id']==1229]
            if ts: rows.append(dict(coach=', '.join(x.get('nickname') or x['name'] for x in (t.get('managers') or [])) or '?', **ts[0]))
A=pd.DataFrame(rows)
SL={ # slider: (season col, match col, invert)
 'Posesión':('team_season_possession','team_match_possession',False),
 'Verticalidad (directness)':('team_season_directness','team_match_directness',False),
 'Velocidad hacia portería':('team_season_pace_towards_goal','team_match_pace_towards_goal',False),
 'Altura de línea defensiva':('team_season_defensive_distance','team_match_defensive_distance',False),
 'Intensidad de presión (PPDA inv.)':('team_season_ppda','team_match_ppda',True),
 'Contrapresión':('team_season_counterpressures_pg','team_match_counterpressures',False),
 'Saque largo del portero':('team_season_gk_long_pass_ratio','team_match_gk_long_pass_ratio',False),
 'Centros al área':('team_season_crosses_into_box_pg','team_match_crosses_into_box',False),
 'Tiros al contragolpe':('team_season_counter_attacking_shots_pg','team_match_counter_attacking_shots',False),
 'Tiros tras presión alta':('team_season_high_press_shots_pg','team_match_high_press_shots',False),
 'xG a favor (np)':('team_season_np_xg_pg','team_match_np_xg',False),
 'xG en contra (np, inv.)':('team_season_np_xg_conceded_pg','team_match_np_xg_conceded',True),
}
res={}
for coach,g in A.groupby('coach'):
    if len(g)<10: continue
    res[coach]={'n':len(g)}
    for k,(sc,mc,inv) in SL.items():
        if sc not in L or mc not in g: res[coach][k]=None; continue
        v=g[mc].mean(); dist=L[sc].dropna()
        p=(dist<v).mean()*100
        res[coach][k]=round(100-p if inv else p)
print(pd.DataFrame(res).to_string())
json.dump(res,open('/tmp/claude-1000/-home-pillofon-Documents-personal-proyectos2026-caon/3c9b0e0c-f7e6-4f4c-b25b-0633a5998d46/scratchpad/sliders.json','w'),ensure_ascii=False)
