"""Exploración: agrupar equipo-entrenador-temporada por estilo, ofensivo y defensivo por separado."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'pipeline'))
from entities import *
import json, collections, numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
ms = all_matches()
rows = []
for m in ms:
    f = CACHE / f"v1_matches_{m['match_id']}_team-stats.json"
    if not f.exists(): continue
    for r in json.load(open(f)):
        side = 'home' if r['team_name'] == m['home_team']['home_team_name'] else 'away'
        coach = (m[side + '_team'].get('managers') or [{}])[0]
        r['coach'] = coach.get('nickname') or coach.get('name', '?'); r['season'] = SEASONS_ALL[m['season']['season_id']]; rows.append(r)
D = pd.DataFrame(rows)
g = lambda c: D['team_match_' + c]
poss = g('possession')
F = pd.DataFrame({'team': D.team_name, 'coach': D.coach, 'season': D.season})
OFF = {'posesion': poss, 'precision_pase': g('passing_ratio'), 'verticalidad': g('directness'), 'velocidad': g('pace_towards_goal'),
       'saque_largo_gk': g('gk_long_pass_ratio'), 'centros_por_llegada': g('crosses_into_box') / g('deep_progressions').clip(lower=1),
       'regates_x_pos': g('total_dribbles') / poss, 'tiro_lejano': g('op_shots_outside_box') / g('op_shots').clip(lower=1),
       'contragolpe': g('counter_attacking_shots') / g('np_shots').clip(lower=1), 'pases_en_area_x_pos': g('passes_inside_box') / poss}
DEF = {'ppda': g('ppda'), 'altura_def': g('defensive_distance'), 'presiones_x_pos_rival': g('pressures') / (1 - poss),
       'presion_campo_rival': g('fhalf_pressures_ratio'), 'contrapresion_x_pos_rival': g('counterpressures') / (1 - poss),
       'agresividad': g('aggression'), 'pase_rival_completado': g('opp_passing_ratio')}
for k, v in {**OFF, **DEF}.items(): F[k] = v.replace([np.inf, -np.inf], np.nan)
U = F.groupby(['team', 'coach', 'season']).agg(['mean', 'size'])
n = U[('posesion', 'size')]; U = U.xs('mean', axis=1, level=1)[n >= 8].dropna()
print('unidades', len(U))
def run(cols, name):
    X = StandardScaler().fit_transform(U[cols])
    best = max(range(3, 7), key=lambda k: silhouette_score(X, KMeans(k, n_init=20, random_state=0).fit_predict(X)))
    for k in range(3, 7): print(name, 'k', k, 'silhouette', round(silhouette_score(X, KMeans(k, n_init=20, random_state=0).fit_predict(X)), 3))
    km = KMeans(best, n_init=50, random_state=0).fit(X)
    Z = pd.DataFrame(km.cluster_centers_, columns=cols)
    lab = pd.Series(km.labels_, index=U.index)
    print(f'\n== {name}: k={best}')
    for c in range(best):
        z = Z.loc[c].sort_values()
        mem = lab[lab == c].index
        print(f'\n[{c}] n={len(mem)}  alto: ' + ', '.join(f'{k} {v:+.1f}' for k, v in z[::-1][:3].items()) + ' | bajo: ' + ', '.join(f'{k} {v:+.1f}' for k, v in z[:3].items()))
        print('   ej:', '; '.join(f'{t} ({c2.split()[-1]}, {s})' for t, c2, s in list(mem)[:14]))
    return lab
lo = run(list(OFF), 'OFENSIVO'); ld = run(list(DEF), 'DEFENSIVO')
pd.DataFrame({'of': lo, 'df': ld}).to_csv(pathlib.Path(__file__).parent / 'clusters.csv')
print('\ncruce ofensivo x defensivo'); print(pd.crosstab(lo, ld))

from sklearn.decomposition import PCA
for cols, name in [(list(OFF), 'OFENSIVO'), (list(DEF), 'DEFENSIVO')]:
    X = StandardScaler().fit_transform(U[cols]); p = PCA(2).fit(X); S = p.transform(X)
    print(f'\nPCA {name}: varianza explicada', p.explained_variance_ratio_.round(2))
    for i in range(2):
        l = pd.Series(p.components_[i], index=cols).sort_values()
        print(f'  eje {i+1}: (+) ' + ', '.join(f'{k} {v:+.2f}' for k, v in l[::-1][:3].items()) + ' | (-) ' + ', '.join(f'{k} {v:+.2f}' for k, v in l[:3].items()))
    sc = pd.DataFrame(S, index=U.index, columns=['e1', 'e2'])
    for key in [('América', 'André Jardine'), ('Atlas', 'Diego Cocca'), ('Guadalajara', 'Gabriel Milito'), ('Guadalajara', 'Fernando Gago'), ('Guadalajara', 'Veljko Paunovic'), ('América', 'Jorge Almada')]:
        sub = sc[[(t == key[0] and key[1].split()[-1] in c) for t, c, s in sc.index]]
        for idx, r in sub.iterrows(): print(f'    {idx[0]:12s} {idx[1]:20s} {idx[2]}  e1 {r.e1:+.2f}  e2 {r.e2:+.2f}')
