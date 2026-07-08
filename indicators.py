"""Indicadores técnicos + Fibonacci + Suporte/Resistência (sem TA-Lib)."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema


def _ema(s, n): return s.ewm(span=n, adjust=False).mean()
def _sma(s, n): return s.rolling(n).mean()

def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def _macd(s, fast=12, slow=26, signal=9):
    macd = _ema(s, fast) - _ema(s, slow)
    sig  = _ema(macd, signal)
    return macd, sig, macd - sig

def _atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def _adx(df, n=14):
    h, l = df["High"], df["Low"]
    up, dn = h.diff(), -l.diff()
    plus_dm  = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr = _atr(df, n)
    pdi = 100 * pd.Series(plus_dm,  index=df.index).ewm(alpha=1/n, adjust=False).mean() / atr
    ndi = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/n, adjust=False).mean() / atr
    dx  = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(alpha=1/n, adjust=False).mean(), pdi, ndi


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    df = df.copy()
    df["EMA9"]   = _ema(df["Close"], cfg.MA_SHORT)
    df["EMA21"]  = _ema(df["Close"], cfg.MA_MID)
    df["SMA50"]  = _sma(df["Close"], cfg.MA_LONG)
    df["SMA200"] = _sma(df["Close"], cfg.MA_TREND)
    df["RSI"]    = _rsi(df["Close"], cfg.RSI_PERIOD)
    macd, sig, hist = _macd(df["Close"], cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL)
    df["MACD"], df["MACD_signal"], df["MACD_hist"] = macd, sig, hist
    adx, pdi, ndi = _adx(df, cfg.ADX_PERIOD)
    df["ADX"], df["DMP"], df["DMN"] = adx, pdi, ndi
    df["ATR"] = _atr(df, cfg.ATR_PERIOD)
    df["VolMean20"] = df["Volume"].rolling(cfg.VOL_LOOKBACK).mean()
    df["OBV"] = (np.sign(df["Close"].diff()).fillna(0) * df["Volume"]).cumsum()
    return df


def find_swing_points(df, lookback=10):
    highs = argrelextrema(df["High"].values, np.greater_equal, order=lookback)[0]
    lows  = argrelextrema(df["Low"].values,  np.less_equal,    order=lookback)[0]
    return list(highs), list(lows)

def fibonacci_levels(hi, lo):
    d = hi - lo
    return {"0.0": lo, "0.236": lo+0.236*d, "0.382": lo+0.382*d, "0.5": lo+0.5*d,
            "0.618": lo+0.618*d, "0.786": lo+0.786*d, "1.0": hi,
            "1.272": hi+0.272*d, "1.618": hi+0.618*d}

def nearest_fib_zone(price, fib, tol=0.015):
    for k, v in fib.items():
        if v > 0 and abs(price - v)/v <= tol:
            return k
    return None

def support_resistance(df, window=20):
    highs, lows = find_swing_points(df, max(window//2, 5))
    p = float(df["Close"].iloc[-1])
    sup = [df["Low"].iloc[i]  for i in lows  if df["Low"].iloc[i]  < p]
    res = [df["High"].iloc[i] for i in highs if df["High"].iloc[i] > p]
    return (max(sup) if sup else None), (min(res) if res else None)
