"""Coleta de dados de mercado via yfinance."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf


def fetch_ohlcv(ticker: str, interval: str, period: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.download(ticker, interval=interval, period=period,
                         progress=False, auto_adjust=True, threads=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.title)
        keep = ["Open", "High", "Low", "Close", "Volume"]
        df = df[[c for c in keep if c in df.columns]].dropna()
        return df if not df.empty else None
    except Exception as e:
        print(f"[fetch_ohlcv] {ticker}: {e}")
        return None


def fetch_universe_data(tickers: List[str], interval: str, period: str,
                        max_workers: int = 10) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_ohlcv, t, interval, period): t for t in tickers}
        for f in as_completed(futs):
            df = f.result()
            if df is not None:
                out[futs[f]] = df
    return out


def passes_liquidity_filter(df: pd.DataFrame, min_price: float,
                            min_avg_volume: float) -> bool:
    if df is None or df.empty or len(df) < 30:
        return False
    return (float(df["Close"].iloc[-1]) >= min_price and
            float(df["Volume"].tail(20).mean()) >= min_avg_volume)
