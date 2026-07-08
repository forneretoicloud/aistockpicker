"""Sistema de score de confluencia + deteccao de data do gatilho."""
from __future__ import annotations
import pandas as pd
from indicators import fibonacci_levels, nearest_fib_zone, find_swing_points, support_resistance
from patterns  import detect_patterns, summarize_pattern


def find_trigger_bar(df, direction: str, lookback: int = 20):
    """Encontra o candle mais recente em que o gatilho principal disparou.
    Prioridade: cruzamento MACD > cruzamento EMA9/21 > RSI saindo de extremo.
    Retorna o indice inteiro do candle ou None.
    """
    if len(df) < 4 or direction == "NEUTRO":
        return None

    n = len(df)
    start = max(1, n - lookback)

    # 1) Cruzamento do MACD histograma (mais preciso)
    mh = df["MACD_hist"].values
    for i in range(n - 1, start, -1):
        if direction == "COMPRA" and mh[i - 1] < 0 <= mh[i]:
            return i
        if direction == "VENDA" and mh[i - 1] > 0 >= mh[i]:
            return i

    # 2) Cruzamento EMA9 x EMA21
    cross = (df["EMA9"] - df["EMA21"]).values
    for i in range(n - 1, start, -1):
        if direction == "COMPRA" and cross[i - 1] < 0 <= cross[i]:
            return i
        if direction == "VENDA" and cross[i - 1] > 0 >= cross[i]:
            return i

    # 3) RSI saindo de sobrevenda / sobrecompra
    rsi = df["RSI"].values
    for i in range(n - 1, start, -1):
        if direction == "COMPRA" and rsi[i - 1] < 30 <= rsi[i]:
            return i
        if direction == "VENDA" and rsi[i - 1] > 70 >= rsi[i]:
            return i

    return None


def compute_score(df, timeframe, cfg):
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last
    price = float(last["Close"])
    reasons, score = [], 0

    # 1) Tendencia
    trend_up   = bool(last["SMA50"] > last["SMA200"]) if pd.notna(last["SMA200"]) else False
    trend_down = bool(last["SMA50"] < last["SMA200"]) if pd.notna(last["SMA200"]) else False
    if trend_up:
        score += 2
        reasons.append("Tendencia de alta (SMA50>SMA200)")
    if trend_down:
        score -= 2
        reasons.append("Tendencia de baixa (SMA50<SMA200)")

    # 2) Cruzamento EMA9 x EMA21
    cross = df["EMA9"] - df["EMA21"]
    if len(cross) >= 4:
        if cross.iloc[-4] < 0 and cross.iloc[-1] > 0:
            score += 2
            reasons.append("Cruzamento de alta EMA9/EMA21")
        elif cross.iloc[-4] > 0 and cross.iloc[-1] < 0:
            score -= 2
            reasons.append("Cruzamento de baixa EMA9/EMA21")

    # 3) ADX
    adx = float(last["ADX"]) if pd.notna(last["ADX"]) else 0
    if adx > 25:
        if trend_up:
            score += 1
            reasons.append(f"ADX forte ({adx:.0f}) a favor da alta")
        if trend_down:
            score -= 1
            reasons.append(f"ADX forte ({adx:.0f}) a favor da baixa")

    # 4) RSI
    rsi = float(last["RSI"]) if pd.notna(last["RSI"]) else 50
    if rsi < 30 and rsi > float(prev["RSI"]):
        score += 2
        reasons.append(f"RSI saindo de sobrevenda ({rsi:.0f})")
    elif rsi > 70 and rsi < float(prev["RSI"]):
        score -= 2
        reasons.append(f"RSI saindo de sobrecompra ({rsi:.0f})")

    # 5) MACD histograma cruzando zero
    if len(df) >= 3:
        h0 = float(df["MACD_hist"].iloc[-2])
        h1 = float(df["MACD_hist"].iloc[-1])
        if h0 < 0 < h1:
            score += 2
            reasons.append("MACD histograma cruzou p/ cima")
        if h0 > 0 > h1:
            score -= 2
            reasons.append("MACD histograma cruzou p/ baixo")

    # 6) Fibonacci
    highs, lows = find_swing_points(df, lookback=10)
    fib_zone = None
    if highs and lows:
        hi_idx = highs[-1]
        lo_idx = lows[-1]
        swing_hi = float(df["High"].iloc[hi_idx])
        swing_lo = float(df["Low"].iloc[lo_idx])
        if swing_hi > swing_lo:
            fib = fibonacci_levels(swing_hi, swing_lo)
            fib_zone = nearest_fib_zone(price, fib, tol=0.015)
            if fib_zone in ("0.5", "0.618"):
                if trend_up:
                    score += 2
                    reasons.append(f"Preco em retracao Fib {fib_zone} (compra)")
                if trend_down:
                    score -= 2
                    reasons.append(f"Preco em retracao Fib {fib_zone} (venda)")

    # 7) Padrao de candle
    patt = detect_patterns(df)
    patt_name, patt_bias = summarize_pattern(patt)
    if patt_bias > 0:
        score += 1
        reasons.append(f"Padrao de alta: {patt_name}")
    if patt_bias < 0:
        score -= 1
        reasons.append(f"Padrao de baixa: {patt_name}")

    # 8) Volume
    volr = 1.0
    if pd.notna(last["VolMean20"]) and last["VolMean20"] > 0:
        volr = float(last["Volume"]) / float(last["VolMean20"])
    if volr > 1.5:
        if score > 0:
            score += 1
            reasons.append(f"Volume {volr:.1f}x acima da media")
        if score < 0:
            score -= 1
            reasons.append(f"Volume {volr:.1f}x acima da media")

    # Direcao final
    if score >= cfg.SCORE_THRESHOLD_BUY:
        direction = "COMPRA"
    elif score <= cfg.SCORE_THRESHOLD_SELL:
        direction = "VENDA"
    else:
        direction = "NEUTRO"

    # Entrada / Stop / Alvo
    atr = float(last["ATR"]) if pd.notna(last["ATR"]) else price * 0.02
    entry = price
    stop = target = risk = None
    if direction == "COMPRA":
        sup, _ = support_resistance(df)
        stop = min(sup, price - cfg.ATR_STOP_MULT * atr) if sup else price - cfg.ATR_STOP_MULT * atr
        risk = entry - stop
        target = entry + cfg.DEFAULT_RR * risk
    elif direction == "VENDA":
        _, res = support_resistance(df)
        stop = max(res, price + cfg.ATR_STOP_MULT * atr) if res else price + cfg.ATR_STOP_MULT * atr
        risk = stop - entry
        target = entry - cfg.DEFAULT_RR * risk

    rr = cfg.DEFAULT_RR if risk else None

    # ==== DATA DO GATILHO ====
    trigger_idx = find_trigger_bar(df, direction) if direction != "NEUTRO" else None
    trigger_date = df.index[trigger_idx] if trigger_idx is not None else None
    trigger_price = float(df["Close"].iloc[trigger_idx]) if trigger_idx is not None else None
    bars_ago = (len(df) - 1 - trigger_idx) if trigger_idx is not None else None

    # Variacao do preco desde o gatilho (%)
    price_change_pct = None
    if trigger_price and trigger_price > 0:
        if direction == "COMPRA":
            price_change_pct = (price - trigger_price) / trigger_price * 100
        elif direction == "VENDA":
            price_change_pct = (trigger_price - price) / trigger_price * 100

    return {
        "score": int(score),
        "direction": direction,
        "reasons": reasons,
        "price": price,
        "rsi": rsi,
        "adx": adx,
        "macd_hist": float(last["MACD_hist"]) if pd.notna(last["MACD_hist"]) else 0,
        "trend": "ALTA" if trend_up else ("BAIXA" if trend_down else "LATERAL"),
        "pattern": patt_name,
        "fib_zone": fib_zone,
        "volume_ratio": round(volr, 2),
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_reward": rr,
        # NOVOS campos
        "trigger_date": trigger_date,
        "trigger_price": trigger_price,
        "trigger_idx": trigger_idx,
        "bars_ago": bars_ago,
        "price_change_pct": price_change_pct,
    }
