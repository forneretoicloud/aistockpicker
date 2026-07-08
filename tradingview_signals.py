"""Integracao com TradingView-TA para recomendacoes oficiais."""
from __future__ import annotations
from typing import Optional

try:
    from tradingview_ta import TA_Handler, Interval, Exchange
    HAS_TV = True
except Exception:
    HAS_TV = False


# Mapeia timeframes do StockPicker para intervalos do TradingView
TV_INTERVAL_MAP = {
    "Semanal": "INTERVAL_1_WEEK",
    "Diario":  "INTERVAL_1_DAY",
    "1h":      "INTERVAL_1_HOUR",
    "30min":   "INTERVAL_30_MINUTES",
}

# Bolsas suportadas (US)
US_EXCHANGES = ["NASDAQ", "NYSE", "AMEX"]


def _get_interval(timeframe: str):
    """Converte label do StockPicker para constante do TradingView."""
    if not HAS_TV:
        return None
    interval_name = TV_INTERVAL_MAP.get(timeframe, "INTERVAL_1_DAY")
    return getattr(Interval, interval_name, Interval.INTERVAL_1_DAY)


def fetch_tradingview_signal(ticker: str, timeframe: str = "Diario") -> dict:
    """
    Consulta o TradingView para um ticker e retorna a recomendacao oficial.
    Tenta NASDAQ, NYSE e AMEX ate encontrar.
    """
    empty = {
        "recommendation": "N/A",
        "buy_count": 0,
        "sell_count": 0,
        "neutral_count": 0,
        "ma_recommendation": "N/A",
        "osc_recommendation": "N/A",
        "exchange": "-",
        "available": False,
    }

    if not HAS_TV:
        return empty

    interval = _get_interval(timeframe)

    for exchange in US_EXCHANGES:
        try:
            handler = TA_Handler(
                symbol=ticker.upper(),
                exchange=exchange,
                screener="america",
                interval=interval,
                timeout=8,
            )
            analysis = handler.get_analysis()
            if analysis is None:
                continue

            summary = analysis.summary or {}
            ma = analysis.moving_averages or {}
            osc = analysis.oscillators or {}

            return {
                "recommendation":     summary.get("RECOMMENDATION", "N/A"),
                "buy_count":          int(summary.get("BUY", 0)),
                "sell_count":         int(summary.get("SELL", 0)),
                "neutral_count":      int(summary.get("NEUTRAL", 0)),
                "ma_recommendation":  ma.get("RECOMMENDATION", "N/A"),
                "osc_recommendation": osc.get("RECOMMENDATION", "N/A"),
                "exchange":           exchange,
                "available":          True,
                "indicators":         analysis.indicators or {},
            }
        except Exception:
            continue

    return empty


def tv_to_score(recommendation: str) -> int:
    """Converte recomendacao TradingView em pontos (-2 a +2)."""
    mapping = {
        "STRONG_BUY":  +2,
        "BUY":         +1,
        "NEUTRAL":      0,
        "SELL":        -1,
        "STRONG_SELL": -2,
    }
    return mapping.get(recommendation, 0)


def tv_emoji(recommendation: str) -> str:
    """Emoji visual para a recomendacao."""
    return {
        "STRONG_BUY":  "🟢🟢",
        "BUY":         "🟢",
        "NEUTRAL":     "🟡",
        "SELL":        "🔴",
        "STRONG_SELL": "🔴🔴",
        "N/A":         "⚪",
    }.get(recommendation, "⚪")
