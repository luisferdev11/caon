# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Piezas puras de la historia: números, rangos descriptivos, niveles, hallazgos y capítulos.

Las frases se arman con el valor y el percentil del registro: ``rank`` solo dice «más que» o «menos que» y ``pick``
nunca devuelve el texto «alto» con un percentil bajo la mediana (ni el «bajo» sobre ella). ``contradictions`` revisa
que ningún hallazgo use frases de signo contrario a su percentil principal.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

import framework as fw

NA = 's/d'
HIGH_MIN, LOW_MAX = 65, 35          # niveles descriptivos del percentil (alto ≥65, bajo ≤35)
MEDIAN_BAND = 1.0                    # |p-50| < 1 → «a la par»
EVIDENCE_REQUIRED = ('id', 'value', 'n', 'unit', 'window')
EVIDENCE_OPTIONAL = ('ci', 'ref_pct', 'scope', 'source', 'entity')
HIGH_PHRASES = ('más que la mayoría', 'por encima de la liga', 'entre los más altos', 'por encima de la mayoría',
                'de los mejores', 'muy por encima')
LOW_PHRASES = ('menos que la mayoría', 'por debajo de la liga', 'entre los más bajos', 'por debajo de la mayoría',
               'de los peores', 'muy por debajo')


# ---------------------------------------------------------------- números
def _round(v: float, digits: int) -> Decimal:
    return Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def num(v: Optional[float], digits: int = 2) -> str:
    """Número con a lo más ``digits`` decimales y sin ceros finales (es-MX: punto decimal)."""
    if v is None:
        return NA
    text = format(_round(v, digits), 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def cap(text: str) -> str:
    """Primera letra en mayúscula sin tocar el resto (``capitalize`` bajaría «xG» a «xg»)."""
    return text[:1].upper() + text[1:]


def auto(v: Optional[float]) -> str:
    """Un decimal desde 10 en adelante y dos por debajo (escala legible de cada indicador)."""
    return NA if v is None else num(v, 1 if abs(v) >= 10 else 2)


def pct(v: Optional[float]) -> str:
    """Porcentaje con un decimal: ``59.8 %``."""
    return NA if v is None else f"{num(v, 1)} %"


def signed(v: Optional[float], digits: int = 2) -> str:
    """Diferencia con signo explícito."""
    if v is None:
        return NA
    return ('+' if v > 0 else '') + num(v, digits)


# ---------------------------------------------------------------- rangos y niveles
def rank(p: Optional[float]) -> Optional[str]:
    """Posición descriptiva frente a la referencia (sin juzgar si es bueno o malo)."""
    if p is None:
        return None
    if abs(p - 50) < MEDIAN_BAND:
        return 'a la par de la mitad de los equipos-temporada'
    if p > 50:
        return f'más que {min(99, round(p))} de cada 100 equipos-temporada'
    return f'menos que {min(99, round(100 - p))} de cada 100 equipos-temporada'


STYLE_NAMES = {'posesion': 'posesión', 'verticalidad': 'verticalidad', 'ritmo': 'ritmo de ataque',
               'linea': 'altura de línea', 'volumen_presion': 'volumen de presión', 'presion': 'PPDA',
               'contrapresion': 'contrapresión', 'saque_largo': 'saque largo del portero', 'centros': 'centros al área',
               'contragolpe': 'tiros al contragolpe', 'presion_alta_tiros': 'tiros tras robo alto', 'xg': 'xG a favor',
               'xga': 'solidez defensiva (xG en contra)', 'bp_xg': 'xG a balón parado'}
INVERTED = ('xga',)    # su percentil ya está invertido: alto = mejor


def style_phrase(key: str, p: Optional[float]) -> str:
    """«nombre: más que N de cada 100…» con el nombre humano; en métricas invertidas dice mejor/peor."""
    name = STYLE_NAMES.get(key, key)
    if p is None:
        return f'{name}: sin referencia'
    if key == 'presion':   # percentil invertido: alto = PPDA bajo = corta pronto el pase
        return (f'{name}: más bajo que {min(99, round(p))} de cada 100 equipos-temporada (corta pronto el pase)' if p >= 50 else
                f'{name}: más alto que {min(99, round(100 - p))} de cada 100 equipos-temporada (deja jugar al rival)')
    if key in INVERTED:
        return (f'{name}: mejor que {min(99, round(p))} de cada 100 equipos-temporada' if p >= 50 else
                f'{name}: peor que {min(99, round(100 - p))} de cada 100 equipos-temporada')
    return f'{name}: {rank(p)}'


def level(p: Optional[float]) -> Optional[str]:
    """alto (≥65), medio o bajo (≤35); None sin percentil."""
    if p is None:
        return None
    return 'alto' if p >= HIGH_MIN else ('bajo' if p <= LOW_MAX else 'medio')


def pick(p: Optional[float], texts: dict[str, str]) -> str:
    """Texto del nivel del percentil; sin percentil, el intermedio."""
    return texts[level(p) or 'medio']


def good_pct(ref_pct: Optional[float], mejor: str) -> Optional[float]:
    """Percentil donde alto = mejor (se invierte si «mejor» es bajo)."""
    if ref_pct is None:
        return None
    return ref_pct if mejor == 'alto' else round(100 - ref_pct, 1)


# ---------------------------------------------------------------- evidencia y hallazgos
def ev(record: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Evidencia citable de un registro del contrato; None si falta o no tiene valor."""
    if not record or record.get('value') is None:
        return None
    if record.get('id') not in fw.DEFINITIONS:
        raise KeyError(f"id de métrica desconocido: {record.get('id')}")
    return {k: record[k] for k in EVIDENCE_REQUIRED + EVIDENCE_OPTIONAL if k in record}


def finding(fid: str, chapter: str, components: list[str], title: str, fact: str, interpretation: str,
            records: list[Optional[dict[str, Any]]], action: str, modo: str = 'ambos',
            pct: Optional[float] = None) -> Optional[dict[str, Any]]:
    """Hallazgo {id, capitulo, componentes, titulo, hecho, interpretacion, evidencia, accion, modo, window}.

    ``pct`` es el percentil principal (descriptivo) para la revisión de contradicciones; sin evidencia → None.
    """
    evidence = [e for e in (ev(r) for r in records) if e]
    if not evidence:
        return None
    windows = {e['window'] for e in evidence}
    if len(windows) > 1:
        raise ValueError(f'hallazgo {fid} mezcla ventanas: {sorted(windows)}')
    window = windows.pop()
    out = {'id': fid, 'capitulo': chapter, 'componentes': components, 'titulo': title, 'hecho': fact,
           'interpretacion': interpretation, 'evidencia': evidence, 'accion': action, 'modo': modo,
           'window': window, 'pct_principal': pct}
    if window != 'oficial':   # insignia «Fuera de ventana oficial»: epílogo y evidencia temprana
        out['fuera_de_ventana'] = True
        for e in evidence:
            e['fuera_de_ventana'] = True
    return out


def contradictions(f: dict[str, Any]) -> list[str]:
    """Frases de signo contrario al percentil principal del hallazgo (lista vacía = coherente)."""
    p = f.get('pct_principal')
    if p is None:
        return []
    text = ' '.join(str(f.get(k, '')) for k in ('titulo', 'hecho', 'interpretacion')).lower()
    bad = HIGH_PHRASES if p < 50 else (LOW_PHRASES if p > 50 else ())
    return [f"{f['id']}: «{ph}» con percentil {p}" for ph in bad if ph in text]


def tag_entities(chapters: list[dict[str, Any]], entity: str) -> None:
    """Completa ``entity`` en la evidencia (sin pisar la que ya la trae) para que la auditoría ate cada número."""
    for ch in chapters:
        for f in ch.get('hallazgos') or []:
            for e in f['evidencia']:
                e.setdefault('entity', entity)


def chapter(cid: str, order: int, title: str, findings: list[Optional[dict[str, Any]]],
            conclusion: Optional[str] = None, curioso: Optional[str] = None,
            visual: Optional[str] = None) -> dict[str, Any]:
    """Capítulo con sus hallazgos y el bloque del modo Aficionado (1 conclusión, 1 visual, 1 dato curioso)."""
    items = [f for f in findings if f]
    out = {'id': cid, 'orden': order, 'titulo': title, 'hallazgos': items,
           'aficionado': {'conclusion': conclusion, 'curioso': curioso, 'visual': visual}}
    if not items:
        out['motivo'] = 'sin datos suficientes para este capítulo'
    return out


# ---------------------------------------------------------------- fuente de datos de una entidad
def dig(node: Any, path: tuple) -> Any:
    """Baja por ``path`` (dicts) y devuelve None si falta algún nivel."""
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    return node


class Src:
    """Datos de una entidad y ventana: analysis, KPIs, percentiles de estilo e identidad (solo lectura)."""

    def __init__(self, analysis: dict, kpis: Optional[list], style: dict, identity: dict, window: str, entity: str,
                 label: str, n: int) -> None:
        self.analysis, self.kpi_rows, self.style, self.identity = analysis, kpis or [], style, identity
        self.window, self.entity, self.label, self.n = window, entity, label, n

    def win(self, topic: str) -> dict:
        """Bloque de la ventana de un tema de analysis ({} si el tema falló o no tiene la ventana)."""
        return dig(self.analysis, (topic, 'ventanas', self.window)) or {}

    def rec(self, topic: str, *path: str) -> Optional[dict]:
        """Registro del contrato en analysis[topic].ventanas[ventana] siguiendo ``path``."""
        r = dig(self.win(topic), path)
        return r if isinstance(r, dict) and r.get('value') is not None else None

    def kpi(self, kid: str) -> Optional[dict]:
        return next((k for k in self.kpi_rows if k['id'] == kid and k.get('value') is not None), None)

    def style_ev(self, key: str) -> Optional[dict]:
        """Percentil de estilo (0–100 frente a la liga) como evidencia citable."""
        v = self.style.get(key)
        if v is None or key not in fw.DEFINITIONS:
            return None
        return {'id': key, 'value': v, 'n': self.n, 'unit': 'percentil 0–100 frente a la liga', 'source': 'team-stats',
                'window': self.window, 'entity': self.entity, 'scope': 'percentil'}
