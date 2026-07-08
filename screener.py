"""Varredura do universo + tecnico + fundamentalista + TradingView."""
from __future__ import annotations
import pandas as pd
import config as cfg
from data_loader   import fetch_ohlcv, passes_liquidity_filter
from indicators    import add_indicators
from signals       import compute_score
from fundamentals  import fetch_fundamentals, compute_fundamental_score
from tradingview_signals import fetch_tradingview_signal, tv_to_score


def _final_direction(tech_score, tv_score, fund_score):
    """Combina os 3 scores para dar direcao consolidada."""
    combined = tech_score + tv_score + fund_score
    if combined >= 8:  return "COMPRA_FORTE"
    if combined >= 4:  return "COMPRA"
    if combined <= -8: return "VENDA_FORTE"
    if combined <= -4: return "VENDA"
    return "NEUTRO"


def scan_universe(tickers, timeframe, progress_cb=None,
                  min_price=None, min_vol=None,
                  with_fundamentals=True, with_tradingview=True):
    interval, period = cfg.TIMEFRAMES[timeframe]
    min_price = min_price if min_price is not None else cfg.MIN_PRICE
    min_vol   = min_vol   if min_vol   is not None else cfg.MIN_AVG_VOLUME

    rows = []
    n = len(tickers)
    for i, tk in enumerate(tickers, 1):
        if progress_cb:
            progress_cb(i / n, tk)
        df = fetch_ohlcv(tk, interval, period)
        if not passes_liquidity_filter(df, min_price, min_vol):
            continue
        try:
            df = add_indicators(df, cfg)
            r  = compute_score(df, timeframe, cfg)

            # Fundamentalista
            fund = {}
            fscore = {"score": 0, "direction": "-", "grade": "-"}
            if with_fundamentals:
                fund = fetch_fundamentals(tk)
                fscore = compute_fundamental_score(fund)

            # TradingView
            tv = {"recommendation": "N/A", "buy_count": 0, "sell_count": 0,
                  "neutral_count": 0, "available": False}
            tv_pts = 0
            if with_tradingview:
                tv = fetch_tradingview_signal(tk, timeframe)
                tv_pts = tv_to_score(tv["recommendation"])

            final_dir = _final_direction(r["score"], tv_pts * 3, fscore["score"])
            combined_score = r["score"] + (tv_pts * 3) + fscore["score"]

            trigger_date_str = "-"
            if r.get("trigger_date") is not None:
                trigger_date_str = r["trigger_date"].strftime("%Y-%m-%d %H:%M")

            rows.append({
                "Ticker":     tk,
                "Nome":       (fund.get("name") or tk)[:40],
                "Setor":      fund.get("sector", "-"),
                "Preco":      round(r["price"], 2),
                # Score consolidado
                "Score_Total":  int(combined_score),
                "Direcao_Final": final_dir,
                # Componentes
                "T_Score":    r["score"],
                "T_Direcao":  r["direction"],
                "TV_Signal":  tv["recommendation"],
                "TV_Buy":     tv["buy_count"],
                "TV_Sell":    tv["sell_count"],
                "TV_Neutral": tv["neutral_count"],
                "F_Score":    fscore["score"],
                "F_Direcao":  fscore["direction"],
                "F_Grade":    fscore["grade"],
                # Contexto
                "Tendencia":  r["trend"],
                "RSI":        round(r["rsi"], 1),
                "ADX":        round(r["adx"], 1),
                "Padrao":     r["pattern"],
                "Zona_Fib":   r["fib_zone"] or "-",
                "Vol_Ratio":  r["volume_ratio"],
                # Gatilho
                "Data_Sinal": trigger_date_str,
                "Bars_Atras": r.get("bars_ago"),
                "Var_%_desde_Sinal": (
                    round(r["price_change_pct"], 2)
                    if r.get("price_change_pct") is not None else None
                ),
                # Trade
                "Entrada":  round(r["entry"], 2)  if r.get("entry")  else None,
                "Stop":     round(r["stop"], 2)   if r.get("stop")   else None,
                "Alvo":     round(r["target"], 2) if r.get("target") else None,
                "R/R":      r.get("risk_reward"),
            })
        except Exception as e:
            print(f"[scan] {tk}: {e}")

    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        df_out["abs_final"] = df_out["Score_Total"].abs()
        df_out = df_out.sort_values("abs_final", ascending=False).drop(columns="abs_final")
    return df_out


def analyze_single(ticker, timeframe):
    interval, period = cfg.TIMEFRAMES[timeframe]
    df = fetch_ohlcv(ticker, interval, period)
    if df is None:
        return None, None, None, None, None
    df = add_indicators(df, cfg)
    tech   = compute_score(df, timeframe, cfg)
    fund   = fetch_fundamentals(ticker)
    fscore = compute_fundamental_score(fund)
    tv     = fetch_tradingview_signal(ticker, timeframe)
    return df, tech, fund, fscore, tv
