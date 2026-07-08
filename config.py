"""Configurações globais do StockPicker Dashboard."""

UNIVERSES = {
    "DOW30": ["AAPL","MSFT","AMGN","AXP","BA","CAT","CRM","CSCO","CVX","DIS",
              "DOW","GS","HD","HON","IBM","JNJ","JPM","KO","MCD","MMM",
              "MRK","NKE","PG","TRV","UNH","V","VZ","WMT"],
    "NASDAQ100_TOP": ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO",
                      "COST","NFLX","AMD","PEP","ADBE","CSCO","QCOM","INTC",
                      "AMAT","TXN","AMGN","ISRG","BKNG","VRTX","LRCX","REGN",
                      "ADI","PANW","MU","MRVL","KLAC","ORLY"],
    "SP500_SAMPLE": ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","JPM","V",
                     "UNH","XOM","JNJ","WMT","MA","PG","HD","CVX","LLY","ABBV",
                     "BAC","PFE","KO","PEP","MRK","AVGO","COST","MCD","TMO","DIS",
                     "CSCO","ABT","ACN","ADBE","CRM","NFLX","WFC","AMD","NKE","ORCL",
                     "T","VZ","INTC","QCOM","IBM","GS","BA","CAT","GE","F"],
    "CUSTOM": ["AAPL","MSFT","NVDA","TSLA","AMZN","GOOGL","META","AMD","NFLX",
               "JPM","BAC","GS","XOM","CVX","WMT","KO","DIS","BA","CAT","F",
               "PLTR","SNOW","UBER","COIN","SHOP","PYPL","ROKU"],
}

# label -> (interval yfinance, período histórico)
TIMEFRAMES = {
    "Semanal": ("1wk", "5y"),
    "Diario":  ("1d",  "2y"),
    "1h":      ("60m", "60d"),
    "30min":   ("30m", "60d"),
}

RSI_PERIOD = 14
ADX_PERIOD = 14
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
MA_SHORT, MA_MID, MA_LONG, MA_TREND = 9, 21, 50, 200
VOL_LOOKBACK = 20
ATR_PERIOD = 14

SCORE_THRESHOLD_BUY  =  6
SCORE_THRESHOLD_SELL = -6

MIN_PRICE = 5.0
MIN_AVG_VOLUME = 1_000_000

DEFAULT_RR    = 2.0
ATR_STOP_MULT = 1.5
