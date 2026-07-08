"""StockPicker Dashboard - Streamlit (v2)."""
from __future__ import annotations
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config as cfg
from screener   import scan_universe, analyze_single
from indicators import find_swing_points, fibonacci_levels

st.set_page_config(page_title="StockPicker - US Equities", layout="wide")
st.title("StockPicker - Screener Tecnico + Fundamentalista")
st.caption("Day trade & swing trade | Price action | Fibonacci | MMs | MACD | RSI | ADX + Analise Fundamentalista")


# ============ RENDER DETALHE (reaproveitavel) ============
def render_ticker_detail(ticker: str, tf: str, key_suffix: str = ""):
    """Renderiza grafico + racional tecnico + fundamentalista + TradingView."""
    from tradingview_signals import tv_emoji

    with st.spinner(f"Analisando {ticker}..."):
        df, tech, fund, fscore, tv = analyze_single(ticker, tf)

    if df is None or tech is None:
        st.error(f"Sem dados para {ticker}.")
        return

    name = fund.get("name", ticker) if fund else ticker
    sector = fund.get("sector", "-") if fund else "-"
    industry = fund.get("industry", "-") if fund else "-"
    st.subheader(f"{ticker} — {name}")
    st.caption(f"Setor: **{sector}** | Industria: **{industry}**")

    # Alerta de idade do sinal
    bars_ago = tech.get("bars_ago")
    change_pct = tech.get("price_change_pct")
    if tech["direction"] != "NEUTRO" and bars_ago is not None:
        change_txt = f" | Preco moveu {change_pct:+.2f}% desde entao" if change_pct is not None else ""
        if bars_ago <= 2:
            st.success(f"🎯 Gatilho FRESCO — Sinal disparou ha {bars_ago} candle(s){change_txt}")
        elif bars_ago <= 5:
            st.info(f"⏱️ Sinal recente ({bars_ago} candles atras){change_txt}")
        else:
            st.warning(f"⚠️ Sinal antigo ({bars_ago} candles){change_txt}. Reavalie entrada.")

    # Metricas top
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Preco", f"${tech['price']:.2f}")
    c2.metric("Score Tecnico", tech["score"], tech["direction"])
    tv_rec = tv.get("recommendation", "N/A")
    c3.metric("TradingView", f"{tv_emoji(tv_rec)} {tv_rec}",
              f"Buy:{tv.get('buy_count',0)} Sell:{tv.get('sell_count',0)}")
    c4.metric("Score Fund.", fscore["score"], f"{fscore['direction']} ({fscore['grade']})")
    c5.metric("RSI", f"{tech['rsi']:.1f}")

    # Grafico
    highs, lows = find_swing_points(df, 10)
    fib = None
    if highs and lows:
        hi = float(df["High"].iloc[highs[-1]])
        lo = float(df["Low"].iloc[lows[-1]])
        if hi > lo:
            fib = fibonacci_levels(hi, lo)

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.15, 0.15, 0.15], vertical_spacing=0.02,
        subplot_titles=("Preco + MMs + Fibonacci", "Volume", "RSI", "MACD")
    )
    fig.add_trace(go.Candlestick(x=df.index, open=df.Open, high=df.High,
                                 low=df.Low, close=df.Close, name="OHLC"), 1, 1)
    for col, color_ in [("EMA9","#00d4ff"),("EMA21","#ffb400"),
                        ("SMA50","#a374ff"),("SMA200","#ff5c5c")]:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col,
                                     line=dict(color=color_, width=1)), 1, 1)
    if fib:
        for k, v in fib.items():
            fig.add_hline(y=v, line_dash="dot", line_color="gold",
                          annotation_text=f"Fib {k}: {v:.2f}",
                          annotation_position="right", row=1, col=1)

    if tech.get("entry")  is not None:
        fig.add_hline(y=tech["entry"],  line_color="white", row=1, col=1)
    if tech.get("stop")   is not None:
        fig.add_hline(y=tech["stop"],   line_color="red",   row=1, col=1)
    if tech.get("target") is not None:
        fig.add_hline(y=tech["target"], line_color="lime",  row=1, col=1)

    # Seta do gatilho
    trigger_idx = tech.get("trigger_idx")
    if trigger_idx is not None and 0 <= trigger_idx < len(df):
        trig_date = df.index[trigger_idx]
        if tech["direction"] == "COMPRA":
            trig_price = float(df["Low"].iloc[trigger_idx])
            arrow_color = "#00ff88"
            arrow_symbol = "triangle-up"
            y_pos = trig_price * 0.97
        else:
            trig_price = float(df["High"].iloc[trigger_idx])
            arrow_color = "#ff4444"
            arrow_symbol = "triangle-down"
            y_pos = trig_price * 1.03

        fig.add_trace(go.Scatter(
            x=[trig_date], y=[y_pos], mode="markers+text",
            marker=dict(symbol=arrow_symbol, color=arrow_color,
                        size=22, line=dict(color="white", width=2)),
            text=[f"GATILHO {tech['direction']}"],
            textposition="bottom center" if tech["direction"] == "COMPRA" else "top center",
            textfont=dict(color=arrow_color, size=11),
            name="Gatilho", showlegend=True
        ), 1, 1)
        fig.add_vline(x=trig_date, line_dash="dash", line_color=arrow_color,
                      line_width=1, opacity=0.4, row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df.Volume, name="Vol", marker_color="#888"), 2, 1)
    fig.add_trace(go.Scatter(x=df.index, y=df.RSI, name="RSI",
                             line=dict(color="#ffb400")), 3, 1)
    fig.add_hline(y=70, line_dash="dash", line_color="red",  row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="lime", row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df.MACD_hist, name="MACD hist",
                         marker_color="#00d4ff"), 4, 1)
    fig.add_trace(go.Scatter(x=df.index, y=df.MACD, name="MACD",
                             line=dict(color="#ffb400")), 4, 1)
    fig.add_trace(go.Scatter(x=df.index, y=df.MACD_signal, name="Signal",
                             line=dict(color="#a374ff")), 4, 1)
    fig.update_layout(height=800, xaxis_rangeslider_visible=False,
                      template="plotly_dark", showlegend=True)
    st.plotly_chart(fig, use_container_width=True,
                    key=f"chart_{ticker}_{tf}_{key_suffix}")

    # 3 colunas: Tecnico | TradingView | Fundamentalista
    colA, colB, colC = st.columns(3)

    with colA:
        st.subheader("📊 Racional Tecnico")
        for reason in tech.get("reasons", []):
            st.write(f"- {reason}")
        if tech["direction"] == "NEUTRO":
            st.warning(f"Sinal NEUTRO (score {tech['score']:+d})")
        elif tech.get("entry") and tech.get("stop") and tech.get("target"):
            entry_v = tech["entry"]
            stop_v = tech["stop"]
            target_v = tech["target"]
            rr = tech.get("risk_reward")
            rr_txt = f" | R/R: {rr:.1f}" if rr else ""
            st.info(
                f"**Entrada:** ${entry_v:.2f}\n\n"
                f"**Stop:** ${stop_v:.2f}\n\n"
                f"**Alvo:** ${target_v:.2f}{rr_txt}"
            )

    with colB:
        st.subheader(f"📡 TradingView ({tv.get('exchange','-')})")
        if not tv.get("available"):
            st.caption("Dados do TradingView indisponiveis.")
        else:
            st.metric("Recomendacao Geral",
                      f"{tv_emoji(tv_rec)} {tv_rec}")
            tv_df = pd.DataFrame([
                {"Categoria": "🟢 Compra",  "Qtd": tv.get("buy_count", 0)},
                {"Categoria": "🟡 Neutro",  "Qtd": tv.get("neutral_count", 0)},
                {"Categoria": "🔴 Venda",   "Qtd": tv.get("sell_count", 0)},
            ])
            st.dataframe(tv_df, hide_index=True, use_container_width=True,key=f"tv_df_{ticker}_{key_suffix}")
            st.markdown(f"**Medias Moveis:** {tv.get('ma_recommendation','-')}")
            st.markdown(f"**Osciladores:** {tv.get('osc_recommendation','-')}")

    with colC:
        st.subheader(f"💼 Fundamentalista (Nota {fscore['grade']})")
        indicators_view = {
            "P/L (trailing)":       fund.get("pe"),
            "P/VP":                 fund.get("pb"),
            "EV/EBITDA":            fund.get("ev_ebitda"),
            "ROE (%)":              (fund.get("roe") or 0) * 100 if fund.get("roe") else None,
            "Margem Liq. (%)":      (fund.get("profit_margin") or 0) * 100 if fund.get("profit_margin") else None,
            "Dividend Yield (%)":   (fund.get("dividend_yield") or 0) * 100 if fund.get("dividend_yield") else None,
            "D/E":                  fund.get("debt_to_equity"),
            "Liquidez Corr.":       fund.get("current_ratio"),
        }
        df_ind = pd.DataFrame(
            [(k, f"{v:.2f}" if isinstance(v, (int, float)) else "-")
             for k, v in indicators_view.items()],
            columns=["Indicador", "Valor"]
        )
        st.dataframe(df_ind, hide_index=True, use_container_width=True,key=f"fund_df_{ticker}_{key_suffix}")
        for reason in fscore.get("reasons", []):
            st.write(f"- {reason}")


# ============ SIDEBAR ============
with st.sidebar:
    st.header("Parametros")
    universe_key = st.selectbox("Universo", list(cfg.UNIVERSES.keys()) + ["MANUAL"], index=3)
    manual_input = ""
    if universe_key == "MANUAL":
        manual_input = st.text_area(
            "Tickers (separados por virgula)",
            value="AAPL, MSFT, NVDA, TSLA, AMZN",
            height=100,
            help="Ex.: AAPL, MSFT, NVDA. Espacos e case sao ignorados."
        )
    timeframe    = st.selectbox("Timeframe", list(cfg.TIMEFRAMES.keys()), index=1)
    with_fund    = st.checkbox("Incluir analise fundamentalista", value=True,
                               help="Mais lento (baixa dados adicionais do Yahoo)")
    min_score    = st.slider("Score tecnico minimo (|abs|)", 0, 12, 0)
    max_bars_ago = st.slider("Sinal recente (max candles atras)",1, 30, 5,help="Filtra apenas gatilhos disparados nos ultimos N candles do timeframe")
    min_price    = st.number_input("Preco minimo (US$)", 1.0, 1000.0, cfg.MIN_PRICE)
    min_vol      = st.number_input("Volume medio minimo", 100_000, 50_000_000,
                                    cfg.MIN_AVG_VOLUME, step=100_000)
    with_tv = st.checkbox(
        "Incluir sinal TradingView",
        value=True,
        help="Recomendacao oficial do TradingView. Adiciona ~1s por ticker."
    )
    run = st.button("Executar Scan", type="primary", use_container_width=True)


# ============ RESOLVE TICKERS ============
if universe_key == "MANUAL":
    tickers = [t.strip().upper() for t in manual_input.split(",") if t.strip()]
else:
    tickers = cfg.UNIVERSES[universe_key]


# ============ STATE ============
if "scan_df" not in st.session_state:
    st.session_state.scan_df = pd.DataFrame()
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None
if "detail_tf" not in st.session_state:
    st.session_state.detail_tf = "Diario"


# ============ TABS ============
tab1, tab2, tab3, tab4 = st.tabs(["Screener", "Detalhe do Ativo", "Resumo", "Docs"])


# ------------ EXECUTA SCAN ------------
if run:
    if not tickers:
        st.error("Nenhum ticker informado.")
    else:
        prog = st.progress(0.0, text="Iniciando...")

        def cb(p, tk):
            prog.progress(p, text=f"Analisando {tk} ({p*100:.0f}%)")

        df = scan_universe(
            tickers,
            timeframe,
            progress_cb=cb,
            min_price=min_price,
            min_vol=min_vol,
            with_fundamentals=with_fund,
            with_tradingview=with_tv,
        )
        prog.empty()
        st.session_state.scan_df = df
        st.session_state.selected_ticker = None

        if df.empty:
            st.error(
                f"Nenhum ativo passou nos filtros. "
                f"Reduza Volume ({int(min_vol):,}) ou Preco (${min_price})."
            )
        else:
            st.success(f"Scan concluido: {len(df)} ativos analisados.")

scan_df = st.session_state.scan_df



# ====== TAB 1: SCREENER ============
with tab1:
    if scan_df.empty:
        st.info("Configure na barra lateral e clique **Executar Scan**.")
    else:
        st.success(f"Scan concluido: {len(scan_df)} ativos analisados.")

        # ---- Filtros interativos ----
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            direcoes = sorted(scan_df["T_Direcao"].dropna().unique().tolist())
            filt_dir = st.multiselect("Direcao Tecnica", direcoes, default=direcoes)
        with fc2:
            tendencias = sorted(scan_df["Tendencia"].dropna().unique().tolist())
            filt_trend = st.multiselect("Tendencia", tendencias, default=tendencias)
        with fc3:
            f_dirs = sorted(scan_df["F_Direcao"].dropna().unique().tolist())
            filt_fdir = st.multiselect("Direcao Fund.", f_dirs, default=f_dirs)
        with fc4:
            tv_sigs = sorted(scan_df["TV_Signal"].dropna().unique().tolist())
            filt_tv = st.multiselect("TradingView", tv_sigs, default=tv_sigs)

        f = scan_df[
            (scan_df["Score_Total"].abs() >= min_score) &
            (scan_df["T_Direcao"].isin(filt_dir)) &
            (scan_df["Tendencia"].isin(filt_trend)) &
            (scan_df["F_Direcao"].isin(filt_fdir)) &
            (scan_df["TV_Signal"].isin(filt_tv))
        ].copy()

        # Filtro adicional: apenas sinais recentes
        if "Bars_Atras" in f.columns:
            f = f[(f["Bars_Atras"].isna()) | (f["Bars_Atras"] <= max_bars_ago)]

        if f.empty:
            st.warning("Nenhum ativo apos filtros. Ajuste os parametros acima.")
        else:
            # ---- Tabela clicavel ----
            st.markdown("**Clique em uma linha para ver o detalhe abaixo:**")
            event = st.dataframe(
                f,
                use_container_width=True,
                height=450,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="screener_table",
            )

            # Captura selecao
            selected_rows = event.selection.rows if event and event.selection else []
            if selected_rows:
                idx = selected_rows[0]
                st.session_state.selected_ticker = f.iloc[idx]["Ticker"]

            # Download
            st.download_button(
                "Baixar CSV",
                f.to_csv(index=False).encode("utf-8"),
                file_name=f"scan_{timeframe}.csv",
                mime="text/csv"
            )

            # ---- Detalhe do ticker selecionado ----
            if st.session_state.selected_ticker:
                st.markdown("---")
                st.markdown(f"## 📊 Detalhe: {st.session_state.selected_ticker}")
                render_ticker_detail(st.session_state.selected_ticker,timeframe,key_suffix="tab1")


# ============ TAB 2: DETALHE MANUAL ============
with tab2:
    all_tickers = tickers if tickers else ["AAPL"]
    tk = st.selectbox("Ativo", all_tickers, key="detail_ticker_manual")
    tf = st.selectbox("Timeframe", list(cfg.TIMEFRAMES.keys()),
                      index=1, key="detail_tf_manual")
    if st.button("Analisar", key="btn_detail_manual"):
        render_ticker_detail(tk, tf, key_suffix="tab2")


# ============ TAB 3: RESUMO ============
with tab3:
    if scan_df.empty or "Direcao" not in scan_df.columns:
        st.info("Execute o scan primeiro.")
    else:
        buys  = scan_df[scan_df["Direcao"] == "COMPRA"]
        sells = scan_df[scan_df["Direcao"] == "VENDA"]
        fbuys  = scan_df[scan_df["F_Direcao"] == "COMPRA"] if "F_Direcao" in scan_df.columns else pd.DataFrame()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ativos analisados", len(scan_df))
        c2.metric("Tecnico COMPRA", len(buys))
        c3.metric("Tecnico VENDA", len(sells))
        c4.metric("Fund. COMPRA", len(fbuys))

        st.markdown("---")
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### 🟢 Top 5 COMPRA (Tecnico)")
            st.dataframe(buys.head(5)[["Ticker","Nome","Score","Direcao","F_Direcao"]],
                         hide_index=True, use_container_width=True)
        with col_r:
            st.markdown("### 🔴 Top 5 VENDA (Tecnico)")
            st.dataframe(sells.tail(5)[["Ticker","Nome","Score","Direcao","F_Direcao"]],
                         hide_index=True, use_container_width=True)

        st.markdown("### 🎯 Confluencia Tecnico + Fundamentalista")
        conflu = scan_df[(scan_df["Direcao"] == "COMPRA") & (scan_df["F_Direcao"] == "COMPRA")]
        if conflu.empty:
            st.caption("Nenhum ativo com dupla confluencia.")
        else:
            st.success(f"{len(conflu)} ativo(s) com COMPRA tecnica **e** fundamentalista:")
            st.dataframe(conflu[["Ticker","Nome","Setor","Score","F_Score","F_Grade","Preco"]],
                         hide_index=True, use_container_width=True)


# ============ TAB 4: DOCS ============
with tab4:
    st.markdown("""
### Score Tecnico de Confluencia

| Criterio | Pontos |
|---|---|
| Tendencia SMA50 vs SMA200 | +/-2 |
| Cruzamento EMA9 x EMA21 | +/-2 |
| ADX > 25 | +/-1 |
| RSI saindo de extremo | +/-2 |
| MACD hist cruza zero | +/-2 |
| Preco em Fib 0.5/0.618 | +/-2 |
| Padrao de candle | +/-1 |
| Volume > 1.5x media | +/-1 |

**Score >= +6 → COMPRA | Score <= -6 → VENDA**

---

### Score Fundamentalista

| Categoria | Indicador | Bom | Ruim |
|---|---|---|---|
| **Valuation** | P/L | <= 20 | >= 35 |
| | P/VP | <= 3 | >= 6 |
| | EV/EBITDA | <= 12 | >= 20 |
| **Rentabilidade** | ROE | >= 15% | <= 5% |
| | Margem Liquida | >= 15% | <= 3% |
| **Proventos** | Dividend Yield | >= 3% | - |
| | Payout | <= 80% | > 80% |
| **Endividamento** | Divida/Patrimonio | <= 1.0 | >= 2.5 |
| | Liquidez Corrente | >= 1.5 | < 1.0 |

Notas: **A** (>=5) | **B** (>=2) | **C** (-1 a +1) | **D** (>=-4) | **F** (<-4)

---

### Fonte dos dados
- Precos e volume: **yfinance / Yahoo Finance**
- Indicadores fundamentalistas: **yfinance ticker.info** (dados podem ter latencia)

### Aviso legal
Ferramenta de estudo. Nao e recomendacao financeira. Use gestao de risco (<= 1-2% por operacao).
""")
