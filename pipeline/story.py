# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Historia del portal → ``model/story/jardine.json`` y ``model/story/almada.json``.

La historia solo lee ``model/analysis/<id>.json``, ``model/kpis/<id>.json`` y ``model/model.json`` (percentiles de
estilo): no recalcula métricas. Cada hallazgo cita registros del contrato; las conclusiones usan solo la ventana
oficial y el epílogo (capítulo 12) y lo temprano (Almada en el América) llevan su ventana.

    .venv/bin/python -X utf8 pipeline/story.py
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import labels
import story_almada as sa
import story_ch_a as ca
import story_ch_b as cb
import story_ch_c as cc
import story_ch_d as cd
import story_text as st
from story_text import Src

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL = ROOT / 'model'
VERSION = 'story.v1'
PROTAGONIST, EPILOGUE_ENTITY = 'ame_jardine', 'ame_jardine_epi'
ALMADA_PACHUCA, ALMADA_AMERICA = 'pac_almada', 'ame_almada'
# Componentes del reto (AC-06): cada uno debe tener al menos un hallazgo con evidencia en los capítulos 1–11.
REQUIRED_COMPONENTS = ('construccion', 'progresion', 'ocasiones', 'presion', 'organizacion_defensiva', 'transiciones',
                       'identidad', 'consistencia', 'contexto_localia', 'contexto_rival', 'contexto_marcador',
                       'contexto_minuto', 'roles', 'alineaciones', 'sustituciones', 'bp_ofensivo', 'bp_defensivo', 'bp_entrega_corner',
                       'bp_zonas_remate', 'bp_saques_banda', 'bp_zonas_vulnerables', 'xg',
                       'obv', 'progresivos', 'ppda', 'field_tilt', 'kpis', '360')


def _read(path: pathlib.Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def load_src(entity: str, window: str, root: pathlib.Path = MODEL, model: Optional[dict] = None) -> Optional[Src]:
    """Fuente de una entidad y ventana; None si falta su analítica o su ficha del modelo."""
    analysis = _read(root / 'analysis' / f'{entity}.json')
    model = model if model is not None else (_read(root / 'model.json') or {})
    ent = next((e for e in model.get('entities', []) if e.get('id') == entity), None)
    if analysis is None or ent is None:
        return None
    kpis = ((_read(root / 'kpis' / f'{entity}.json') or {}).get('kpis') or {}).get(window)
    style = ent.get('style') or {}
    return Src(analysis, kpis, style, labels.identity(style), window, entity, ent.get('label', entity), ent.get('n', 0))


def coverage(chapters: list[dict]) -> dict[str, list[str]]:
    """{componente: [ids de hallazgo]} solo con los capítulos de la ventana oficial (1–11)."""
    out: dict[str, list[str]] = {}
    for ch in chapters:
        for f in ch['hallazgos']:
            if f['window'] == 'oficial':
                for comp in f['componentes']:
                    out.setdefault(comp, []).append(f['id'])
    return out


def build_jardine(off: Src, epi: Optional[Src]) -> dict:
    """Los 12 capítulos de la historia de Jardine."""
    chapters = [ca.portada(off), ca.identidad(off), ca.con_balon(off), cb.sin_balon(off), cb.transiciones(off),
                cc.lo_que_mas_dolio(off), cc.balon_parado(off), cc.consistencia_contexto(off), cd.jugadores(off),
                cd.merecio(off), cd.tablero(off)]
    chapters.append(cd.epilogo(epi, off) if epi else {'id': 'epilogo', 'orden': 12, 'titulo': 'Epílogo: 2025/26, fuera de la ventana oficial',
                                                      'hallazgos': [], 'motivo': 'sin analítica del epílogo'})
    for ch in chapters[:11]:
        st.tag_entities([ch], off.entity)
    if epi:
        st.tag_entities(chapters[11:], epi.entity)
    cover = coverage(chapters)
    return {'version': VERSION, 'id': 'jardine', 'titulo': 'La historia de André Jardine en el América',
            'entidad': off.entity, 'etiqueta': off.label, 'ventana': 'oficial', 'partidos': off.n,
            'capitulos': chapters, 'cobertura': {c: cover.get(c, []) for c in REQUIRED_COMPONENTS},
            'nota': 'Descriptivo: asociaciones y comparaciones con la liga; no aísla el efecto del entrenador. '
                    'El epílogo (capítulo 12) está fuera de la ventana oficial.'}


def main(argv: list[str]) -> int:
    from model_split import dump_json
    model = _read(MODEL / 'model.json') or {}
    off, epi = load_src(PROTAGONIST, 'oficial', MODEL, model), load_src(EPILOGUE_ENTITY, 'epilogo', MODEL, model)
    if off is None:
        print('falta la analítica de', PROTAGONIST, flush=True)
        return 1
    (MODEL / 'story').mkdir(parents=True, exist_ok=True)
    doc = build_jardine(off, epi)
    dump_json(doc, MODEL / 'story' / 'jardine.json')
    n = sum(len(c['hallazgos']) for c in doc['capitulos'])
    print(f"  jardine: {len(doc['capitulos'])} capítulos, {n} hallazgos, sin cubrir: "
          f"{[c for c, v in doc['cobertura'].items() if not v]}", flush=True)
    pac, ame = load_src(ALMADA_PACHUCA, 'oficial', MODEL, model), load_src(ALMADA_AMERICA, 'temprano', MODEL, model)
    explorer = _read(MODEL / 'explorer.json') or {}
    if pac is None or ame is None:
        print('  almada: falta la analítica de Pachuca·Almada o América·Almada', flush=True)
        return 1
    almada = sa.build_almada(pac, ame, off, explorer)
    dump_json(almada, MODEL / 'story' / 'almada.json')
    print(f"  almada: {len(almada['capitulos'])} capítulos, {sum(len(c['hallazgos']) for c in almada['capitulos'])} hallazgos", flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
