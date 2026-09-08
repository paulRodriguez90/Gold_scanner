from __future__ import annotations
from dataclasses import dataclass
from typing import Any


def clamp(x: float, lo=-100.0, hi=100.0) -> float:
    return max(lo, min(hi, float(x)))

@dataclass(frozen=True)
class MacroFactor:
    name: str
    score: float
    direction: str
    reason: str
    data_date: str | None = None

@dataclass(frozen=True)
class MacroImpact:
    score: float
    state: str
    factors: tuple[MacroFactor, ...]
    explanation: str
    missing: tuple[str, ...]
    next_fomc: str | None = None


def _direction(score: float) -> str:
    if score >= 20: return "BULLISH GOLD"
    if score <= -20: return "BEARISH GOLD"
    return "NEUTRAL"


def _trend_score(delta: float | None, scale: float, positive_bullish: bool) -> float:
    if delta is None: return 0.0
    raw = clamp(delta / scale) * 100.0
    return raw if positive_bullish else -raw


def _obs(history: list[dict[str, Any]], n: int) -> dict[str, Any] | None:
    return history[n] if n < len(history) else None


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0): return None
    return (a / b - 1.0) * 100.0


def _inflation_factor(snapshot: dict) -> MacroFactor:
    cpi = snapshot.get("cpi_core") or snapshot.get("cpi_all_items")
    ppi = snapshot.get("ppi_core") or snapshot.get("ppi_final_demand")
    signals = []
    dates = []
    details = []
    for label, hist in (("CPI", cpi), ("PPI", ppi)):
        if not hist: continue
        cur = _obs(hist, 0); prev = _obs(hist, 1); year = _obs(hist, 12)
        if not cur: continue
        mom = _pct(cur["value"], prev["value"] if prev else None)
        yoy = _pct(cur["value"], year["value"] if year else None)
        # Rising inflation is bearish for gold; falling inflation is bullish.
        s1 = _trend_score(mom, 0.30, False)
        s2 = _trend_score(yoy, 3.0, False)
        s = (s1 + s2) / 2 if (mom is not None and yoy is not None) else (s1 if mom is not None else s2)
        signals.append(s); dates.append(cur.get("date")); details.append(f"{label} MoM={mom:+.2f}% YoY={yoy:+.2f}%" if mom is not None and yoy is not None else label)
    if not signals:
        return MacroFactor("inflation", 0, "NEUTRAL", "Sin datos de inflación suficientes")
    score = clamp(sum(signals) / len(signals))
    return MacroFactor("inflation", score, _direction(score), "; ".join(details), max(dates) if dates else None)


def _employment_factor(snapshot: dict) -> MacroFactor:
    nfp = snapshot.get("nonfarm_payrolls") or []
    unemp = snapshot.get("unemployment_rate") or []
    scores = []; details=[]; dates=[]
    if nfp:
        cur=_obs(nfp,0); prev=_obs(nfp,1)
        if cur and prev:
            change = cur["value"] - prev["value"]
            # Weaker payroll growth is bullish gold. +/- 150k maps to +/-100.
            s = _trend_score(change, 150.0, False)
            scores.append(s); dates.append(cur.get("date")); details.append(f"NFP cambio={change:+.0f}k")
    if unemp:
        cur=_obs(unemp,0); prev=_obs(unemp,1)
        if cur and prev:
            delta = cur["value"] - prev["value"]
            # Rising unemployment is bullish gold.
            s = _trend_score(delta, 0.30, True)
            scores.append(s); dates.append(cur.get("date")); details.append(f"desempleo cambio={delta:+.2f} pp")
    if not scores:
        return MacroFactor("employment",0,"NEUTRAL","Sin datos de empleo suficientes")
    score=clamp(sum(scores)/len(scores))
    return MacroFactor("employment",score,_direction(score),"; ".join(details),max(dates) if dates else None)


def _fed_factor(snapshot: dict) -> MacroFactor:
    target=snapshot.get("target_range") or {}
    history=snapshot.get("target_history") or []
    if not target.get("lower") or not target.get("upper"):
        return MacroFactor("fed",0,"NEUTRAL","Sin rango objetivo de la Fed")
    current=(target["lower"]+target["upper"])/2
    prior=None
    if len(history)>1:
        prior=(history[1]["lower"]+history[1]["upper"])/2
    if prior is None:
        return MacroFactor("fed",0,"NEUTRAL","Rango Fed disponible; sin cambio previo verificable",target.get("date"))
    change=current-prior
    # Lower policy rate is bullish gold; higher is bearish.
    score=clamp(-change/0.50*100)
    reason=f"cambio del punto medio={change:+.2f} pp"
    return MacroFactor("fed",score,_direction(score),reason,target.get("date"))


def calculate_macro_impact(snapshot: dict) -> MacroImpact:
    factors=[]; missing=[]
    for fn,name in ((_inflation_factor,"inflation"),(_employment_factor,"employment"),(_fed_factor,"fed")):
        f=fn(snapshot); factors.append(f)
        if f.reason.startswith("Sin datos"):
            missing.append(name)
    weights={"inflation":0.40,"employment":0.30,"fed":0.30}
    score=clamp(sum(f.score*weights[f.name] for f in factors))
    if score>=60: state="COMPRA FUERTE"
    elif score>=30: state="COMPRA MODERADA"
    elif score>=10: state="ALCISTA — ESPERAR"
    elif score>-10: state="INDECISION"
    elif score>-30: state="BAJISTA — ESPERAR"
    elif score>-60: state="VENTA MODERADA"
    else: state="VENTA FUERTE"
    if missing and state in {"COMPRA FUERTE","COMPRA MODERADA"}: state="ALCISTA — ESPERAR"
    if missing and state in {"VENTA FUERTE","VENTA MODERADA"}: state="BAJISTA — ESPERAR"
    explanation="; ".join(f"{f.name} {f.score:+.1f}" for f in factors)
    if missing: explanation += ". Datos faltantes: " + ", ".join(missing)
    return MacroImpact(round(score,1),state,tuple(factors),explanation,tuple(missing),snapshot.get("next_fomc"))


def _latest_event(events, key: str):
    rows = [e for e in (events or []) if getattr(e, "key", None) == key and getattr(e, "released", False)]
    return max(rows, key=lambda e: e.date) if rows else None


def _surprise_score(actual, consensus, scale, positive_bullish=True):
    if actual is None or consensus is None:
        return None
    surprise = actual - consensus
    raw = clamp(surprise / scale) * 100.0
    return raw if positive_bullish else -raw


def _latest_event(events, keys):
    if isinstance(keys, str):
        keys = (keys,)
    rows = [e for e in (events or []) if getattr(e, "key", None) in keys and getattr(e, "released", False)]
    return max(rows, key=lambda e: (e.date, e.release_time or "")) if rows else None


def _surprise_score(actual, consensus, scale, positive_bullish=True):
    if actual is None or consensus is None:
        return None
    surprise = actual - consensus
    raw = clamp(surprise / scale) * 100.0
    return raw if positive_bullish else -raw


def calculate_surprise_impact(snapshot: dict, events=None) -> dict:
    """Calculate actual-vs-consensus surprise and expose upcoming consensus.

    Consensus is never inferred. Released events contribute to the score;
    future events are reported separately so their forecasts can be monitored
    before the release.
    """
    events = events or []
    specs = [
        (("cpi",), "CPI", 0.20, False),
        (("core_cpi",), "Core CPI", 0.15, False),
        (("ppi",), "PPI", 0.30, False),
        (("core_ppi",), "Core PPI", 0.25, False),
        (("nfp",), "NFP", 150_000.0, False),
        (("unemployment",), "Unemployment", 0.15, True),
    ]
    labels = {k[0]: label for k, label, _, _ in specs}
    scales = {k[0]: (scale, bullish) for k, _, scale, bullish in specs}
    released_rows = []
    upcoming_rows = []
    missing_consensus = []
    for e in events:
        if e.key not in labels:
            continue
        label = labels[e.key]
        scale, positive_bullish = scales[e.key]
        if e.actual is None:
            if e.consensus is not None:
                upcoming_rows.append({"key": e.key, "label": label, "consensus": e.consensus, "previous": e.previous, "date": e.date, "source": e.source, "release_time": e.release_time})
            continue
        if e.consensus is None:
            missing_consensus.append(label)
            continue
        score = _surprise_score(e.actual, e.consensus, scale, positive_bullish)
        released_rows.append({
            "key": e.key, "label": label, "actual": e.actual,
            "consensus": e.consensus, "previous": e.previous,
            "surprise": e.actual - e.consensus, "score": round(score, 1),
            "date": e.date, "source": e.source, "release_time": e.release_time,
        })
    # Keep only the latest released event per indicator for scoring.
    latest = {}
    for row in released_rows:
        current = latest.get(row["key"])
        if current is None or (row["date"], row.get("release_time") or "") > (current["date"], current.get("release_time") or ""):
            latest[row["key"]] = row
    rows = list(latest.values())
    upcoming_rows.sort(key=lambda r: (r["date"], r["key"]))
    if not rows:
        msg = "No hay consenso disponible para calcular sorpresas."
        if missing_consensus:
            msg += " Sin consenso: " + ", ".join(sorted(set(missing_consensus)) ) + "."
        return {"score": 0.0, "state": "SIN CONSENSO", "events": [], "upcoming": upcoming_rows, "missing_consensus": sorted(set(missing_consensus)), "explanation": msg}
    weights = {"cpi": .20, "core_cpi": .20, "ppi": .15, "core_ppi": .10, "nfp": .20, "unemployment": .15}
    total_w = sum(weights[r["key"]] for r in rows)
    score = clamp(sum(r["score"] * weights[r["key"]] for r in rows) / total_w)
    if score >= 30: state = "FAVORABLE AL ORO"
    elif score <= -30: state = "DESFAVORABLE AL ORO"
    else: state = "MIXTO / LEVE"
    explanation = "; ".join(f'{r["label"]} {r["score"]:+.1f}' for r in rows)
    if missing_consensus:
        explanation += "; sin consenso: " + ", ".join(sorted(set(missing_consensus)))
    return {"score": round(score,1), "state": state, "events": rows, "upcoming": upcoming_rows, "missing_consensus": sorted(set(missing_consensus)), "explanation": explanation}
