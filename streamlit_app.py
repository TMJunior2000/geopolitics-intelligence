import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime
import pytz
from typing import cast

# 1. CARICA LE VARIABILI D'AMBIENTE
load_dotenv()

# --- IMPORTS LOCALI ---
# Assicurati che detect_fvgs sia definito in backend/analysis.py
from backend.analysis import detect_fvgs 
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import (
    render_trump_section, 
    render_carousel, 
    render_all_assets_sections, 
    _generate_html_card
)
from backend.broker import TradingAccount
from backend.risk_engine import SurvivalRiskEngine
from backend.strategy import TrafficLightSystem
from frontend.ui.lightweight_chart import render_lightweight_chart

# ---------------------------------------------------------
# 1. SETUP PAGINA & CSS
# ---------------------------------------------------------
st.set_page_config(page_title="Market Intelligence AI", page_icon="🦅", layout="wide")

# Carica il CSS
load_css("style.css")

# ---------------------------------------------------------
# 2. GESTIONE DATI & STATO
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    try:
        repo = MarketRepository()
        raw = repo.get_all_insights_flat()
        if not raw: return pd.DataFrame()
        df = pd.DataFrame(raw)
        for col in ['published_at', 'created_at']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
        return df.sort_values(by='published_at', ascending=False)
    except Exception as e:
        print(f"⚠️ Errore caricamento dati: {e}")
        return pd.DataFrame()

df = load_data()

# Inizializzazione Sistemi Backend
if 'broker' not in st.session_state:
    st.session_state.broker = TradingAccount(balance=200.0)
    st.session_state.risk_engine = SurvivalRiskEngine(st.session_state.broker)
    st.session_state.strategy = TrafficLightSystem(st.session_state.broker)

# ---------------------------------------------------------
# 3. HEADER & NAVIGAZIONE IBRIDA
# ---------------------------------------------------------
st.markdown("""
<div style="padding: 10px 0 0 0; margin-bottom: 25px;">
    <h1 style="font-size: 38px; letter-spacing: -1px; margin: 0;">Market <span style="color:#2ECC71">Intelligence</span> AI</h1>
</div>
""", unsafe_allow_html=True)

all_tickers = sorted(df['asset_ticker'].dropna().astype(str).unique().tolist()) if not df.empty else []

# Align Nav and Search
col_nav, col_search = st.columns([2.5, 1], gap="medium", vertical_alignment="bottom")

with col_nav:
    nav_options = ["🦅 DASHBOARD", "🇺🇸 TRUMP WATCH", "🧠 MARKET INSIGHTS"]
    selected_view = st.radio("Nav", options=nav_options, horizontal=True, label_visibility="collapsed")

with col_search:
    clean_tickers = [t for t in all_tickers if t.strip()]
    search_options = ["TUTTI"] + clean_tickers
    selected_asset_search = st.selectbox(
        "Search", 
        options=search_options, 
        index=0, 
        label_visibility="visible"
    )

# ---------------------------------------------------------
# 4. LOGICA DI VISUALIZZAZIONE
# ---------------------------------------------------------

if selected_view == "🦅 DASHBOARD":
    
    # ==============================================================================
    # 1. ZONE: KAIROS HUD (Statistiche Conto)
    # ==============================================================================
    acct = st.session_state.broker.get_account_info()
    margin_class = "money" if acct['free_margin'] > 100 else "risk" if acct['free_margin'] > 50 else "danger"
    oxy_color = '#EF4444' if margin_class == 'danger' else '#F8FAFC'
    open_positions = st.session_state.broker.get_positions()
    
    # HTML HEADER
    html_header = (
        f'<div style="background: rgba(15, 23, 42, 0.9); padding: 15px 25px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: space-between;">'
        f'<div style="display:flex; align-items:center;">'
        f'<span style="font-size: 10px; color: #94A3B8; margin-right: 8px; font-weight: 700; letter-spacing: 1px;">BALANCE</span>'
        f'<span style="font-family: \'Space Grotesk\'; font-weight: 700; color: #F8FAFC; font-size: 18px; margin-right: 25px;">${acct["balance"]:,.2f}</span>'
        f'<span style="border-left:1px solid #334155; height:16px; margin:0 15px;"></span>'
        f'<span style="font-size: 10px; color: #94A3B8; margin-right: 8px; font-weight: 700; letter-spacing: 1px;">EQUITY</span>'
        f'<span style="font-family: \'Space Grotesk\'; font-weight: 700; color: #2ECC71; font-size: 18px; margin-right: 25px; text-shadow: 0 0 15px rgba(46,204,113,0.2);">${acct["equity"]:,.2f}</span>'
        f'<span style="border-left:1px solid #334155; height:16px; margin:0 15px;"></span>'
        f'<span style="font-size: 10px; color: #94A3B8; margin-right: 8px; font-weight: 700; letter-spacing: 1px;">OXYGEN</span>'
        f'<span style="font-family: \'Space Grotesk\'; font-weight: 700; font-size: 18px; color: {oxy_color}">${acct["free_margin"]:,.0f}</span>'
        f'</div>'
        f'<div><span style="font-family: monospace; font-size: 11px; color: #475569; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px;">ID: {acct.get("login", "N/A")}</span></div>'
        f'</div>'
    )

    if not open_positions:
        html_body = (
            '<div style="padding: 12px 25px; background: rgba(2, 6, 23, 0.4); min-height: 45px; display: flex; align-items: center;">'
            '<div style="color: #64748B; font-size: 13px; display: flex; align-items: center; font-style: italic;">'
            '<span style="font-size: 16px; margin-right: 10px; opacity: 0.7;">💤</span>'
            '<span>Nessuna posizione aperta. Flat Market.</span>'
            '</div></div>'
        )
    else:
        traffic_signals = st.session_state.strategy.analyze_portfolio(df) if not df.empty else []
        cards = ""
        for pos in open_positions:
            sig = next((s for s in traffic_signals if s['ticker'] == pos['symbol']), None)
            color = "#2ECC71" if sig and sig['status'] == "GREEN" else "#EF4444" if sig and sig['status'] == "RED" else "#94A3B8"
            bg_color = f"{color}10"
            pnl_color = "#2ECC71" if pos['profit'] >= 0 else "#EF4444"
            
            cards += (
                f'<div style="border-left: 3px solid {color}; background: linear-gradient(90deg, {bg_color} 0%, rgba(0,0,0,0) 100%); padding: 6px 12px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05); min-width: 140px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">'
                f'<span style="font-weight:700; font-size:12px; color: #F1F5F9;">{pos["symbol"]}</span>'
                f'<span style="font-size:9px; background:rgba(255,255,255,0.1); padding:1px 4px; border-radius:3px; color:#CBD5E1;">{pos["type"]}</span>'
                f'</div>'
                f'<div style="font-size:13px; font-family:monospace; font-weight:700; color: {pnl_color};">{pos["profit"]:+.2f} $</div>'
                f'</div>'
            )
        html_body = f'<div style="padding: 12px 25px; background: rgba(2, 6, 23, 0.4); display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">{cards}</div>'

    st.markdown(f'<div class="hud-container">{html_header}{html_body}</div>', unsafe_allow_html=True)

    # ==============================================================================
    # 2. ZONE: EXECUTION DECK
    # ==============================================================================
    with st.container(border=True):
        
        # A. TITOLO
        st.markdown("""
            <div style="display:flex; align-items:center; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;">
                <span style="color:#F59E0B; margin-right: 12px; font-size: 20px;">⚡</span>
                <span style="font-family:'Space Grotesk'; font-weight:700; color:#F8FAFC; font-size:16px; letter-spacing: 1px;">EXECUTION DECK</span>
            </div>
        """, unsafe_allow_html=True)

        # B. SELEZIONE ASSET
        live_assets = st.session_state.broker.get_all_available_tickers()
        live_assets.sort()
        
        default_index = 0
        if selected_asset_search and selected_asset_search != "TUTTI" and selected_asset_search in live_assets:
            default_index = live_assets.index(selected_asset_search)
        
        c_asset, c_tf, c_empty = st.columns([1.5, 0.8, 2], gap="medium", vertical_alignment="center")
        
        with c_asset:
             target_ticker = st.selectbox("ASSET", live_assets, index=default_index, label_visibility="collapsed")
        with c_tf:
             selected_tf = st.radio("TF", ["H4", "M15"], index=0, horizontal=True, label_visibility="collapsed")

        # C. DATI & GRAFICO (PRIMA DEGLI INPUT)
        specs = st.session_state.broker.get_asset_specs(target_ticker) if target_ticker else None
        tick_info = st.session_state.broker.get_latest_tick(target_ticker) if target_ticker else None
        current_price = float(tick_info['price']) if tick_info else 0.0

        if target_ticker:
            n_candles = 200 if selected_tf == "H4" else 500
            candles_df = st.session_state.broker.get_candles(target_ticker, timeframe=selected_tf, n_candles=n_candles)
            
            if not candles_df.empty:
                # 1. Analisi FVG
                candles_df['time'] = pd.to_datetime(candles_df['time'])
                fvgs_found = detect_fvgs(candles_df)
                active_fvgs = [f for f in fvgs_found if f['mitigated_pct'] < 98]

                # 2. RENDER GRAFICO (SOPRA)
                render_lightweight_chart(
                    df=candles_df, 
                    ticker=target_ticker, 
                    fvgs=active_fvgs # Passiamo solo gli FVG
                )
            else:
                st.warning(f"Dati non disponibili per {target_ticker}")

        # D. INPUT GRID (SOTTO IL GRAFICO)
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns([0.8, 1, 1, 1, 1.2], gap="small", vertical_alignment="top")
        
        contract_size = specs['contract_size'] if specs else 1
        leverage_val = specs.get('leverage', 50) if specs else 50
        default_sl = current_price * 0.99
        default_tp = current_price * 1.02

        with c1:
            min_l = float(specs['min_lot']) if specs else 0.01
            step_l = float(specs.get('step_lot', 0.01)) if specs else 0.01
            selected_size = st.number_input("SIZE", min_value=min_l, value=min_l, step=step_l, format="%.2f")
            
            notional = current_price * selected_size * contract_size
            margin_req = notional / leverage_val if leverage_val else 0
            st.markdown(f"""
                <div style='font-family:monospace; font-size:11px; color:#64748B; margin-top:-10px; line-height:1.2;'>
                    MARGIN: <span style='color:#F8FAFC'>${margin_req:.2f}</span> 
                    <span style='margin: 0 3px; opacity: 0.3;'>|</span> 
                    LEVA: <span style='color:#F59E0B'>1:{leverage_val:.0f}</span>
                </div>
            """, unsafe_allow_html=True)
        
        with c2:
            entry_price = st.number_input("ENTRY", value=current_price, step=0.01, format="%.2f", key=f"entry_{target_ticker}")
            st.markdown("<div style='height: 13px;'></div>", unsafe_allow_html=True)
            
        with c3:
            sl_input = st.number_input("STOP LOSS", value=default_sl, step=0.01, format="%.2f", key=f"sl_{target_ticker}")
            dist_sl = entry_price - sl_input
            money_sl = abs(dist_sl) * selected_size * contract_size
            pct_sl = (abs(dist_sl)/entry_price)*100 if entry_price else 0
            risk_color = "#EF4444" if money_sl > (acct['equity']*0.02) else "#94A3B8"
            st.markdown(f"<div style='font-family:monospace; font-size:11px; color:{risk_color}; margin-top:-10px;'>RISK: -${money_sl:.1f} ({pct_sl:.1f}%)</div>", unsafe_allow_html=True)
            
        with c4:
            tp_input = st.number_input("TAKE PROFIT", value=default_tp, step=0.01, format="%.2f", key=f"tp_{target_ticker}")
            dist_tp = tp_input - entry_price
            money_tp = abs(dist_tp) * selected_size * contract_size
            risk_reward = money_tp / money_sl if money_sl > 0 else 0
            st.markdown(f"<div style='font-family:monospace; font-size:11px; color:#2ECC71; margin-top:-10px;'>TARGET: +${money_tp:.1f} (R:{risk_reward:.1f})</div>", unsafe_allow_html=True)

        with c5:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 
            if st.button("VERIFY TRADE", type="primary", use_container_width=True):
                check = st.session_state.risk_engine.check_trade_feasibility(target_ticker, "LONG", entry_price, sl_input)
                if check['allowed']:
                    st.toast(f"✅ Trade SAFE! Max Lots: {check['max_lots']}", icon="🛡️")
                else:
                    st.toast(f"❌ REJECTED: {check['reason']}", icon="💀")

    # ==============================================================================
    # 3. ZONE: INTELLIGENCE FEED (CARD)
    # ==============================================================================
    # Questa sezione DEVE essere qui. Se il codice sopra (chart) crasha, questa parte non viene eseguita.
    if not df.empty:
        if selected_asset_search and selected_asset_search != "TUTTI":
            asset_df = df[df['asset_ticker'] == selected_asset_search].copy()
            if not asset_df.empty:
                st.markdown(f"### 🔎 Risultati per {selected_asset_search}")
                cards_html = "".join([_generate_html_card(row) for _, row in asset_df.iterrows()])
                st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
            else:
                st.info(f"Nessuna news recente per {selected_asset_search}.")
        else:
            # Renderizza le caroselle se "TUTTI"
            render_carousel(df)
            render_all_assets_sections(df)

elif selected_view == "🇺🇸 TRUMP WATCH":
    if not df.empty:
        render_trump_section(df)
    else:
        st.info("Dati non disponibili per Trump Watch.")

elif selected_view == "🧠 MARKET INSIGHTS":
    if not df.empty:
        render_all_assets_sections(df)
    else:
        st.info("Dati non disponibili.")

st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)