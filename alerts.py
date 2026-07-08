"""Alertas via Telegram."""
from __future__ import annotations
import requests, pandas as pd

def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": chat_id, "text": message,
                                      "parse_mode": "Markdown"}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[Telegram] {e}")
        return False


def check_and_alert(scan_df: pd.DataFrame, min_abs_score: int,
                    bot_token: str, chat_id: str) -> int:
    if scan_df.empty: return 0
    strong = scan_df[scan_df["Score"].abs() >= min_abs_score]
    n = 0
    for _, r in strong.iterrows():
        emoji = "🟢" if r["Direção"] == "COMPRA" else "🔴"
        msg = (f"{emoji} *{r['Ticker']}* — {r['Direção']} (score {r['Score']:+d})\n"
               f"Preço: ${r['Preço'\]:.2f} | RSI {r['RSI']} | ADX {r['ADX']}\n"
               f"Entrada ${r['Entrada']} | Stop ${r['Stop']} | Alvo ${r['Alvo']}\n"
               f"Padrão: {r['Padrão']} | Fib: {r['Zona_Fib']}")
        if send_telegram_alert(bot_token, chat_id, msg): n += 1
    return n
