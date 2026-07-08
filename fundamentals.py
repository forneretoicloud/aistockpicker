"""Analise fundamentalista via yfinance (ticker.info)."""
from __future__ import annotations
import yfinance as yf


# Thresholds para o score fundamentalista (mercado US)
FUND_THRESHOLDS = {
    "pe_good":       20,    # P/L abaixo disso e bom
    "pe_bad":        35,    # P/L acima disso e ruim
    "pb_good":       3,     # P/VP
    "pb_bad":        6,
    "ev_ebitda_good": 12,   # EV/EBITDA
    "ev_ebitda_bad": 20,
    "roe_good":      0.15,  # 15%
    "roe_bad":       0.05,
    "margin_good":   0.15,  # margem liquida 15%
    "margin_bad":    0.03,
    "dy_good":       0.03,  # 3%
    "payout_max":    0.80,  # payout saudavel <= 80%
    "de_good":       1.0,   # divida/patrimonio <= 1
    "de_bad":        2.5,
    "curr_ratio_good": 1.5, # liquidez corrente >= 1.5
}


def fetch_fundamentals(ticker: str) -> dict:
    """Busca indicadores fundamentalistas de um ticker via yfinance."""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:
        print(f"[fundamentals] {ticker}: {e}")
        return {}

    def _pct(v):
        return float(v) if v is not None else None

    return {
        "name":         info.get("longName") or info.get("shortName") or ticker,
        "sector":       info.get("sector", "-"),
        "industry":     info.get("industry", "-"),
        "country":      info.get("country", "-"),
        "market_cap":   info.get("marketCap"),
        # Valuation
        "pe":           info.get("trailingPE"),
        "forward_pe":   info.get("forwardPE"),
        "pb":           info.get("priceToBook"),
        "ev_ebitda":    info.get("enterpriseToEbitda"),
        # Rentabilidade
        "roe":          _pct(info.get("returnOnEquity")),
        "roa":          _pct(info.get("returnOnAssets")),
        "profit_margin":_pct(info.get("profitMargins")),
        "op_margin":    _pct(info.get("operatingMargins")),
        # Proventos
        "dividend_yield": _pct(info.get("dividendYield")),
        "payout_ratio":   _pct(info.get("payoutRatio")),
        # Endividamento
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio":  info.get("currentRatio"),
        "quick_ratio":    info.get("quickRatio"),
    }


def _score_metric(value, good, bad, higher_is_better=True):
    """Retorna +1 (bom), -1 (ruim), 0 (neutro/indefinido)."""
    if value is None:
        return 0
    if higher_is_better:
        if value >= good: return +1
        if value <= bad:  return -1
    else:
        if value <= good: return +1
        if value >= bad:  return -1
    return 0


def compute_fundamental_score(fund: dict) -> dict:
    """Score fundamentalista (-10 a +10) + direcao + racional."""
    if not fund:
        return {"score": 0, "direction": "NEUTRO", "reasons": [], "grade": "-"}

    T = FUND_THRESHOLDS
    reasons, score = [], 0

    # ---- Valuation (menor = melhor) ----
    s = _score_metric(fund.get("pe"), T["pe_good"], T["pe_bad"], higher_is_better=False)
    if s: reasons.append(f"P/L {fund['pe']:.1f} ({'atrativo' if s>0 else 'caro'})")
    score += s

    s = _score_metric(fund.get("pb"), T["pb_good"], T["pb_bad"], higher_is_better=False)
    if s: reasons.append(f"P/VP {fund['pb']:.2f} ({'atrativo' if s>0 else 'caro'})")
    score += s

    s = _score_metric(fund.get("ev_ebitda"), T["ev_ebitda_good"], T["ev_ebitda_bad"], higher_is_better=False)
    if s: reasons.append(f"EV/EBITDA {fund['ev_ebitda']:.1f} ({'bom' if s>0 else 'alto'})")
    score += s

    # ---- Rentabilidade (maior = melhor) ----
    s = _score_metric(fund.get("roe"), T["roe_good"], T["roe_bad"])
    if s: reasons.append(f"ROE {fund['roe']*100:.1f}% ({'forte' if s>0 else 'fraco'})")
    score += s

    s = _score_metric(fund.get("profit_margin"), T["margin_good"], T["margin_bad"])
    if s: reasons.append(f"Margem liq. {fund['profit_margin']*100:.1f}% ({'boa' if s>0 else 'fraca'})")
    score += s

    # ---- Proventos ----
    dy = fund.get("dividend_yield")
    if dy is not None and dy >= T["dy_good"]:
        score += 1; reasons.append(f"DY {dy*100:.2f}% (bom pagador)")
    pay = fund.get("payout_ratio")
    if pay is not None and 0 < pay <= T["payout_max"]:
        score += 1; reasons.append(f"Payout {pay*100:.0f}% (sustentavel)")
    elif pay is not None and pay > T["payout_max"]:
        score -= 1; reasons.append(f"Payout {pay*100:.0f}% (alto demais)")

    # ---- Endividamento (menor = melhor) ----
    de = fund.get("debt_to_equity")
    if de is not None:
        de_norm = de / 100 if de > 10 else de  # yfinance as vezes retorna em %
        if de_norm <= T["de_good"]:
            score += 1; reasons.append(f"D/E {de_norm:.2f} (baixo)")
        elif de_norm >= T["de_bad"]:
            score -= 1; reasons.append(f"D/E {de_norm:.2f} (alto)")

    cr = fund.get("current_ratio")
    if cr is not None:
        if cr >= T["curr_ratio_good"]:
            score += 1; reasons.append(f"Liquidez corr. {cr:.2f} (saudavel)")
        elif cr < 1:
            score -= 1; reasons.append(f"Liquidez corr. {cr:.2f} (aperto)")

    # ---- Classificacao ----
    if   score >=  5: direction, grade = "COMPRA", "A"
    elif score >=  2: direction, grade = "COMPRA", "B"
    elif score >= -1: direction, grade = "NEUTRO", "C"
    elif score >= -4: direction, grade = "VENDA",  "D"
    else:             direction, grade = "VENDA",  "F"

    return {"score": score, "direction": direction, "reasons": reasons, "grade": grade}
