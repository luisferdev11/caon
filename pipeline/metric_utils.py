"""Numerical contracts shared by analytical summaries (never impute absence)."""
import math


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def ratio(num, den):
    return num / den if finite(num) and finite(den) and den > 0 else None


def event_metrics(m):
    # Missing counter keys in legacy extracts are observed zeros only if the
    # extract contains a match. An empty metric object has no observations.
    if not m:
        return {}
    get = lambda k: m.get(k, 0) if finite(m.get(k, 0)) else None
    passes, opponent = get('passes'), get('opp_passes')
    poss = ratio(passes, passes + opponent) if passes is not None and opponent is not None else None
    ppda = ratio(get('opp_passes_own60'), get('ppda_den'))
    return {
        'team_match_possession': poss,
        'team_match_directness': ratio(get('dir_fwd'), get('dir_tot')),
        'team_match_pace_towards_goal': ratio(get('pace2_sum'), get('pace2_n')),
        'team_match_defensive_distance': ratio(get('def_x'), get('def_n')),
        'team_match_pressures_adj': ratio(get('pressures'), 1 - poss) if poss is not None else None,
        'team_match_ppda': math.log(ppda) if ppda is not None and ppda > 0 else None,
        'team_match_counterpressures': get('counterpressures'),
        'team_match_gk_long_pass_ratio': ratio(get('gk_long'), get('gk_passes')),
        'team_match_crosses_into_box': get('crosses_box'),
        'team_match_counter_attacking_shots': get('counter_shots2'),
        'team_match_high_press_shots': get('high_press_shots'),
        'team_match_np_xg': get('np_xg'),
        'team_match_np_xg_conceded': get('np_xga'),
        'team_match_sp_xg': get('sp_xg'),
    }


def fit_calibration(pairs):
    import numpy as np
    valid = [(x, y) for x, y in pairs if finite(x) and finite(y)]
    if len(valid) < 3:
        return None, 'calibracion_sin_pares_suficientes'
    x, y = np.array(valid).T
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return None, 'calibracion_sin_variacion'
    b, a = np.polyfit(x, y, 1)
    r2 = float(np.corrcoef(x, y)[0, 1] ** 2)
    if not all(finite(float(v)) for v in (a, b, r2)):
        return None, 'calibracion_no_finita'
    return (float(a), float(b), r2), None if r2 >= .5 else 'calibracion_r2_inferior_0.5'
