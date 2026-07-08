"""Backtest simples da estratégia de score de confluência."""
from __future__ import annotations
import numpy as np
import pandas as pd
import config as cfg
from data_loader import fetch_ohlcv
from indicators  import add_indicators
from signals     import compute_score


def backtest_strategy(ticker: str, timeframe: str, risk_pct: float = 0.02,
                      capital_inicial: float = 10_000, warmup: int = 210) -> dict:
    interval, period = cfg.TIMEFRAMES[timeframe]
    df = fetch_ohlcv(ticker, interval, period)
    if df is None or len(df) < warmup + 20:
        return {"error": "Dados insuficientes"}
    df = add_indicators(df, cfg)

    capital = capital_inicial
    equity_curve = [capital]
    trades, in_pos, side, entry, stop, target = [], False, None, None, None, None

    for i in range(warmup, len(df)):
        window = df.iloc[: i + 1]
        price  = float(df["Close"].iloc[i])

        if in_pos:
            hit_stop   = (side == "L" and price <= stop) or (side == "S" and price >= stop)
            hit_target = (side == "L" and price >= target) or (side == "S" and price <= target)
            if hit_stop or hit_target:
                pnl_pct = ((price - entry) / entry) if side == "L" else ((entry - price) / entry)
                pnl_$   = capital * risk_pct * (pnl_pct / abs((entry - stop) / entry))
                capital += pnl_$
                trades.append({"side": side, "entry": entry, "exit": price,
                               "pnl_pct": pnl_pct, "pnl_$": pnl_$,
                               "result": "WIN" if pnl_$ > 0 else "LOSS"})
                in_pos = False
        else:
            r = compute_score(window, timeframe, cfg)
            if r["direction"] == "COMPRA":
                in_pos, side, entry, stop, target = True, "L", r["entry"], r["stop"], r["target"]
            elif r["direction"] == "VENDA":
                in_pos, side, entry, stop, target = True, "S", r["entry"], r["stop"], r["target"]

        equity_curve.append(capital)

    if not trades:
        return {"error": "Nenhum trade gerado", "trades": 0}

    tdf = pd.DataFrame(trades)
    wins   = tdf[tdf["pnl_$"] > 0]["pnl_$"].sum()
    losses = -tdf[tdf["pnl_$"] < 0]["pnl_$"].sum()
    eq = pd.Series(equity_curve)
    dd = (eq / eq.cummax() - 1).min()
    rets = eq.pct_change().dropna()
    sharpe = (rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0

    return {
        "trades":        len(tdf),
        "win_rate":      round((tdf["pnl_$"] > 0).mean() * 100, 1),
        "profit_factor": round(wins / losses, 2) if losses > 0 else float("inf"),
        "total_return":  round((capital / capital_inicial - 1) * 100, 1),
        "max_drawdown":  round(dd * 100, 1),
        "sharpe":        round(sharpe, 2),
        "final_capital": round(capital, 2),
        "equity_curve":  equity_curve,
    }


if __name__ == "__main__":
    import sys
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    tf = sys.argv[2] if len(sys.argv) > 2 else "Diario"
    print(backtest_strategy(tk, tf))
