import streamlit as st
from dotenv import load_dotenv
import os

# 1. CARICA LE VARIABILI PRIMA DI TUTTO
load_dotenv()

import pandas as pd
import datetime # Per gestione orari
import pytz # Per gestione fusi orari
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import render_trump_section, render_carousel, render_all_assets_sections, _generate_html_card, render_market_section
from backend.broker import TradingAccount
from backend.risk_engine import SurvivalRiskEngine
from backend.strategy import TrafficLightSystem

# 1. SETUP PAGE
st.set_page_config(page_title="Market Intelligence AI", page_icon="🦅", layout="wide")
load_css("style.css")

@st.cache_data(ttl=300)
def load_data():
    try:
        repo = MarketRepository()
        raw = repo.get_all_insights_flat()
        
        if not raw:
            return pd.DataFrame()
            
        df = pd.DataFrame(raw)
        
        # Conversione date sicura
        for col in ['published_at', 'created_at']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
                
        return df.sort_values(by='published_at', ascending=False)
        
    except Exception as e:
        print(f"⚠️ Errore caricamento dati: {e}")
        return pd.DataFrame()

df = load_data()

# 0. INIZIALIZZA SISTEMI (Mock)
if 'broker' not in st.session_state:
    st.session_state.broker = TradingAccount(balance=200.0) # Conto da $200
    st.session_state.risk_engine = SurvivalRiskEngine(st.session_state.broker)
    st.session_state.strategy = TrafficLightSystem(st.session_state.broker)

# ---------------------------------------------------------
# 3. HEADER & NAVIGAZIONE IBRIDA
# ---------------------------------------------------------

# Titolo
st.markdown("""
<div style="padding: 10px 0 0 0; margin-bottom: 20px;">
    <h1 style="font-size: 38px; letter-spacing: -1px; margin: 0;">Market <span style="color:#2ECC71">Intelligence</span> AI</h1>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Caricamento dati...")
    st.stop()

# --- LAYOUT NAVIGAZIONE (2 Colonne) ---
col_nav, col_search = st.columns([2.2, 1])

# A. Colonna Sinistra: MENU
with col_nav:
    nav_options = ["🦅 DASHBOARD", "🇺🇸 TRUMP WATCH", "🧠 MARKET INSIGHTS"]
    selected_view = st.radio("Nav", options=nav_options, horizontal=True, label_visibility="collapsed")

# B. Colonna Destra: RICERCA (La logica di filtro verrà applicata dopo)
with col_search:
    # Qui usiamo ancora i ticker dal DB per la ricerca delle news
    all_tickers = sorted(df['asset_ticker'].dropna().astype(str).unique().tolist())
    clean_tickers = [t for t in all_tickers if t.strip()]
    search_options = ["TUTTI"] + clean_tickers
    
    selected_asset_search = st.selectbox(
        "Search", 
        options=search_options, 
        index=None, 
        placeholder="🔍 Cerca Asset...", 
        label_visibility="collapsed"
    )

# ---------------------------------------------------------
# 4. LOGICA DI VISUALIZZAZIONE
# ---------------------------------------------------------

if selected_view == "🦅 DASHBOARD":
    
    # === A. KAIROS TRADING DESK (STILE HUD/CARD) ===
    
    # Recupera dati account
    acct = st.session_state.broker.get_account_info()
    
    # Calcolo classi CSS
    margin_class = "money" if acct['free_margin'] > 100 else "risk" if acct['free_margin'] > 50 else "danger"
    
    # VISUALIZZA STATO CONTO AGGIORNATO
    st.markdown(f"""
    <div class="trading-card-container">
        <div class="trading-header" style="display:flex; justify-content:space-between; align-items:center;">
            <span>🛡️ KAIROS TRADING HUD</span>
            <span style="font-size: 12px; opacity: 0.7; font-family: monospace;">ACC: {acct['login']}</span>
        </div>
        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-label">💰 Balance</div>
                <div class="metric-value">${acct['balance']:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">📈 Equity</div>
                <div class="metric-value money">${acct['equity']:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">🔒 Used Margin</div>
                <div class="metric-value">${acct['used_margin']:.2f}</div>
            </div>
            <div class="metric-box" style="border-color: rgba(255,255,255,0.1);">
                <div class="metric-label">🫁 Free Oxygen</div>
                <div class="metric-value {margin_class}">${acct['free_margin']:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_desk_L, col_desk_R = st.columns([1.5, 1])

    # 2. SEMAFORO POSIZIONI APERTE (COLONNA SINISTRA)
    with col_desk_L:
        # Wrapper grafico inizio
        st.markdown("""
        <div class="trading-card-container" style="min-height: 380px;">
            <div class="trading-header">
                <span>🚦 LIVE POSITIONS & SIGNALS</span>
            </div>
        """, unsafe_allow_html=True)

        open_positions = st.session_state.broker.get_positions()
        
        if not open_positions:
            st.info("😴 Nessuna posizione aperta. Il desk è tranquillo.")
            st.markdown("<br>"*5, unsafe_allow_html=True) # Spacer
        else:
            traffic_signals = st.session_state.strategy.analyze_portfolio(df)
            if not traffic_signals:
                st.info("✅ Posizioni stabili. Nessun alert dall'AI.")
            
            for signal in traffic_signals:
                color_hex = "#2ECC71" if signal['status'] == "GREEN" else "#F59E0B" if signal['status'] == "YELLOW" else "#EF4444"
                bg_hex = f"{color_hex}15" # 15 è alpha hex per trasparenza
                
                # Card interna per il segnale
                with st.container():
                    st.markdown(f"""
                    <div style="background:{bg_hex}; border-left: 4px solid {color_hex}; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:700; color:#FFF; font-size:16px;">{signal['ticker']}</span>
                            <span style="font-size:10px; background:#0F172A; padding:2px 6px; border-radius:4px; color:{color_hex}; border:1px solid {color_hex};">{signal['status']}</span>
                        </div>
                        <div style="font-size:12px; color:#CBD5E1; margin-top:5px;"><i>"{signal['msg']}"</i></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if signal['status'] == "RED":
                        if st.button(f"CHIUDI {signal['ticker']}", key=f"close_{signal['ticker']}", type="primary", use_container_width=True):
                             # Qui andrebbe la logica di chiusura
                             st.toast(f"Ordine chiusura {signal['ticker']} inviato!", icon="🚀")

        # Wrapper grafico fine
        st.markdown("</div>", unsafe_allow_html=True)

    # --- COLONNA DESTRA: CALCOLATORE DINAMICO ---
    with col_desk_R:
        st.markdown("""
        <div class="trading-card-container" style="min-height: 420px; border-color: rgba(46, 204, 113, 0.3);">
            <div class="trading-header">
                <span>📊 SMART MARGIN CALCULATOR</span>
            </div>
        """, unsafe_allow_html=True)

        live_assets = st.session_state.broker.get_all_available_tickers()
        live_assets.sort()
        
        # Gestione sicura dell'indice per evitare errore str | None
        d_idx = 0
        if selected_asset_search is not None and selected_asset_search in live_assets:
            try:
                d_idx = live_assets.index(selected_asset_search)
            except ValueError:
                d_idx = 0
        
        target_ticker = st.selectbox("Asset", live_assets, index=d_idx, key="hud_ticker")

        specs = st.session_state.broker.get_asset_specs(target_ticker)
        tick_info = st.session_state.broker.get_latest_tick(target_ticker)

        if specs and tick_info:
            price = tick_info['price']
            
            # 1. INPUT SIZE DINAMICA
            col_inp, col_res = st.columns([1, 1])
            with col_inp:
                selected_size = st.number_input(
                    "Size (Lots)",
                    min_value=float(specs['min_lot']),
                    value=float(specs['min_lot']),
                    step=0.01 if specs['min_lot'] < 1 else 1.0,
                    format="%.2f"
                )
            
            # 2. CALCOLO DINAMICO
            # Valore Nozionale = Prezzo * Lotti * Dimensione Contratto
            notional = price * selected_size * specs['contract_size']
            # Margine = Nozionale / Leva (rispetta il blocco 1:50)
            required_margin = notional / specs['leverage']

            with col_res:
                st.markdown(f"""
                <div style="background:rgba(46,204,113,0.1); border:1px solid #2ECC71; padding:10px; border-radius:8px; text-align:center; margin-top:25px;">
                    <div style="font-size:10px; color:#94A3B8;">MARGINE REALE</div>
                    <div style="font-size:24px; font-weight:700; color:#2ECC71;">${required_margin:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            st.caption(f"Leva: 1:{specs['leverage']} | Nozionale: ${notional:.2f} | Prezzo: {price}")
            
            # 3. RISK ENGINE INTEGRATION
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1: stop_loss = st.number_input("Stop Loss", value=0.0, format="%.2f")
            with c2: 
                if st.button("🧮 CALCOLA SIZE SICURA", use_container_width=True):
                    res = st.session_state.risk_engine.check_trade_feasibility(target_ticker, "LONG", price, stop_loss)
                    if res['allowed']: st.success(f"Size OK: {res['max_lots']} lotti")
                    else: st.error(res['reason'])

        st.markdown("</div>", unsafe_allow_html=True)

    # === B. FEED CONTENUTI ===
    if selected_asset_search and selected_asset_search != "TUTTI":
        asset_df = df[df['asset_ticker'] == selected_asset_search].copy()
        if not asset_df.empty:
            cards_html = "".join([_generate_html_card(row) for _, row in asset_df.iterrows()])
            st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
    else:
        render_carousel(df)
        render_all_assets_sections(df)

elif selected_view == "🇺🇸 TRUMP WATCH":
    render_trump_section(df)

elif selected_view == "🧠 MARKET INSIGHTS":
    render_all_assets_sections(df)

st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)