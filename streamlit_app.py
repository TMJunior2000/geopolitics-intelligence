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
    
    # === A. KAIROS TRADING HUD (TOP BAR) ===
    acct = st.session_state.broker.get_account_info()
    margin_class = "money" if acct['free_margin'] > 100 else "risk" if acct['free_margin'] > 50 else "danger"
    
    st.markdown(f"""
    <div class="trading-card-container">
        <div class="trading-header">
            <span>🛡️ KAIROS TRADING HUD</span>
            <span style="font-family: monospace; opacity: 0.5;">ID: {acct['login']}</span>
        </div>
        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-label">Balance</div>
                <div class="metric-value">${acct['balance']:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Equity</div>
                <div class="metric-value money">${acct['equity']:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Used Margin</div>
                <div class="metric-value">${acct['used_margin']:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Free Oxygen</div>
                <div class="metric-value {margin_class}">${acct['free_margin']:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_desk_L, col_desk_R = st.columns([1.3, 1.2])

    # === B. LIVE SIGNALS (COLONNA SINISTRA) ===
    with col_desk_L:
        st.markdown('<div class="trading-card-container desk-column-box">', unsafe_allow_html=True)
        st.markdown('<div class="trading-header"><span>🚦 LIVE SIGNALS</span></div>', unsafe_allow_html=True)
        
        open_positions = st.session_state.broker.get_positions()
        if not open_positions:
            st.info("😴 Nessuna posizione attiva.")
        else:
            traffic_signals = st.session_state.strategy.analyze_portfolio(df)
            for signal in traffic_signals:
                color = "#2ECC71" if signal['status'] == "GREEN" else "#F59E0B" if signal['status'] == "YELLOW" else "#EF4444"
                st.markdown(f"""
                <div style="background:{color}10; border-left: 3px solid {color}; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid {color}20;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-weight:700; color:#FFF;">{signal['ticker']}</span>
                        <span style="font-size:9px; color:{color}; font-weight:800;">{signal['status']}</span>
                    </div>
                    <div style="font-size:11px; color:#94A3B8; margin-top:4px;">{signal['msg']}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # === C. SMART MARGIN CALCULATOR (COLONNA DESTRA) ===
    with col_desk_R:
        st.markdown('<div class="trading-card-container desk-column-box">', unsafe_allow_html=True)
        st.markdown('<div class="trading-header"><span>📊 MARGIN CALCULATOR</span></div>', unsafe_allow_html=True)
        
        # Logica Tickers e Index (Fix Pylance)
        available_tickers = st.session_state.broker.get_all_available_tickers()
        available_tickers.sort()
        d_idx = 0
        if selected_asset_search is not None and selected_asset_search in available_tickers:
            d_idx = available_tickers.index(selected_asset_search)
        
        target_ticker = st.selectbox("Asset Target", available_tickers, index=d_idx, key="calc_asset")
        
        specs = st.session_state.broker.get_asset_specs(target_ticker)
        tick = st.session_state.broker.get_latest_tick(target_ticker)

        if specs and tick:
            # Inputs
            c1, c2 = st.columns([1, 1])
            with c1:
                size = st.number_input("Lots", min_value=float(specs['min_lot']), step=0.01, value=float(specs['min_lot']), format="%.2f")
            
            # Calcolo Dinamico
            notional = tick['price'] * size * specs['contract_size']
            margin_req = notional / specs['leverage']

            with c2:
                st.markdown(f"""
                <div class="margin-res-box">
                    <div style="font-size:9px; color:#64748B; font-weight:700;">REQUIRED MARGIN</div>
                    <div style="font-size:22px; font-weight:700; color:#2ECC71;">${margin_req:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:10px; margin-top:10px;">
                <div style="display:flex; justify-content:space-between; font-size:11px;">
                    <span style="color:#64748B;">Leva Reale</span><span style="color:#F8FAFC; font-weight:600;">1:{int(specs['leverage'])}</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-top:4px;">
                    <span style="color:#64748B;">Nozionale</span><span style="color:#F8FAFC; font-weight:600;">${notional:.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            sl = st.number_input("Stop Loss Price", value=0.0, step=0.01, format="%.2f")
            if st.button("🧮 CALCOLA RISCHIO", use_container_width=True, type="primary"):
                # Integrazione Risk Engine qui
                pass
        
        st.markdown('</div>', unsafe_allow_html=True)

    # D. Titolo Daily Feed
    st.markdown('<div class="section-header header-market"><h3>📡 Intelligence Live Feed</h3></div>', unsafe_allow_html=True)

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