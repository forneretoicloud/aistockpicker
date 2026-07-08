"""Detecção de padrões de candles (last bar)."""
from __future__ import annotations
import pandas as pd

def detect_patterns(df: pd.DataFrame) -> dict:
    if len(df) < 3: return {}
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    body   = (c - o).abs()
    rng    = (h - l).replace(0, 1e-9)
    upper  = h - c.where(c >= o, o)
    lower  = o.where(c >= o, c) - l
    bull   = c > o
    bear   = c < o

    i = -1
    p = {
        "hammer":            bool(bull.iloc[i] and lower.iloc[i] > 2*body.iloc[i] and upper.iloc[i] < body.iloc[i]),
        "shooting_star":     bool(bear.iloc[i] and upper.iloc[i] > 2*body.iloc[i] and lower.iloc[i] < body.iloc[i]),
        "doji":              bool(body.iloc[i] <= 0.1*rng.iloc[i]),
        "marubozu_bull":     bool(bull.iloc[i] and body.iloc[i] >= 0.9*rng.iloc[i]),
        "marubozu_bear":     bool(bear.iloc[i] and body.iloc[i] >= 0.9*rng.iloc[i]),
        "bullish_engulfing": bool(bear.iloc[i-1] and bull.iloc[i] and c.iloc[i] > o.iloc[i-1] and o.iloc[i] < c.iloc[i-1]),
        "bearish_engulfing": bool(bull.iloc[i-1] and bear.iloc[i] and o.iloc[i] > c.iloc[i-1] and c.iloc[i] < o.iloc[i-1]),
    }
    if len(df) >= 3:
        p["morning_star"] = bool(bear.iloc[i-2] and body.iloc[i-1] < body.iloc[i-2]*0.5 and bull.iloc[i] and c.iloc[i] > (o.iloc[i-2]+c.iloc[i-2])/2)
        p["evening_star"] = bool(bull.iloc[i-2] and body.iloc[i-1] < body.iloc[i-2]*0.5 and bear.iloc[i] and c.iloc[i] < (o.iloc[i-2]+c.iloc[i-2])/2)
        p["three_white_soldiers"] = bool(bull.iloc[i] and bull.iloc[i-1] and bull.iloc[i-2] and c.iloc[i] > c.iloc[i-1] > c.iloc[i-2])
        p["three_black_crows"]    = bool(bear.iloc[i] and bear.iloc[i-1] and bear.iloc[i-2] and c.iloc[i] < c.iloc[i-1] < c.iloc[i-2])
    return p

def summarize_pattern(p: dict) -> tuple[str, int]:
    """Retorna (nome_padrão, viés). viés: +1 alta, -1 baixa, 0 neutro."""
    bullish = ["hammer","bullish_engulfing","morning_star","three_white_soldiers","marubozu_bull"]
    bearish = ["shooting_star","bearish_engulfing","evening_star","three_black_crows","marubozu_bear"]
    for name in bullish:
        if p.get(name): return name, +1
    for name in bearish:
        if p.get(name): return name, -1
    if p.get("doji"): return "doji", 0
    return "-", 0
