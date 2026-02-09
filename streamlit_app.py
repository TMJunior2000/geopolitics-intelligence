import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import datetime
import pytz

# 1. CARICA LE VARIABILI D'AMBIENTE
load_dotenv()

# --- IMPORTS LOCALI (Assicurati che questi moduli esistano nel tuo progetto) ---
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

# ---------------------------------------------------------
# 1. SETUP PAGINA & CSS
# ---------------------------------------------------------
st.set_page_config(page_title="Market Intelligence AI", page_icon="🦅", layout="wide")

# Carica il CSS esterno (se esiste)
load_css("style.css")

# INIEZIONE CSS AGGIUNTIVO PER IL TRADING DESK (Per garantire lo stile Glassmorphism)
st.markdown("""
<style>
    /* TRADING DESK CONTAINER */
    .trading-card-container {
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(46, 204, 113, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }
    .trading-header {
        font-family: 'Space Grotesk', sans-serif;
        color: #F8FAFC;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 15px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        padding-bottom: 10px;
    }
    
    /* METRICS HUD */
    .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
    .metric-box {
        background: rgba(2, 6, 23, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
    }
    .metric-label { font-size: 10px; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 1px; }
    .metric-value { font-family: 'Space Grotesk', monospace; font-size: 24px; font-weight: 700; color: #F8FAFC; }
    .metric-value.money { color: #2ECC71; text-shadow: 0 0 15px rgba(46, 204, 113, 0.2); }
    .metric-value.risk { color: #F59E0B; }
    .metric-value.danger { color: #EF4444; text-shadow: 0 0 15px rgba(239, 68, 68, 0.2); }

    /* INPUT LABEL FIX */
    div[data-testid="stNumberInput"] label {
        font-family: 'Space Grotesk', sans-serif;
        color: #94A3B8; font-size: 12px; text-transform: uppercase; font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

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
<div style="padding: 10px 0 0 0; margin-bottom: 20px;">
    <h1 style="font-size: 38px; letter-spacing: -1px; margin: 0;">Market <span style="color:#2ECC71">Intelligence</span> AI</h1>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Caricamento dati in corso o database vuoto...")
    # Non mettiamo st.stop() qui per permettere almeno al Trading Desk di funzionare se connesso
else:
    all_tickers = sorted(df['asset_ticker'].dropna().astype(str).unique().tolist())

col_nav, col_search = st.columns([2.2, 1])

with col_nav:
    nav_options = ["🦅 DASHBOARD", "🇺🇸 TRUMP WATCH", "🧠 MARKET INSIGHTS"]
    selected_view = st.radio("Nav", options=nav_options, horizontal=True, label_visibility="collapsed")

with col_search:
    # Logica per la search bar globale
    clean_tickers = [t for t in (all_tickers if not df.empty else []) if t.strip()]
    search_options = ["TUTTI"] + clean_tickers
    
    selected_asset_search = st.selectbox(
        "Search", 
        options=search_options, 
        index=0, 
        placeholder="🔍 Cerca Asset...", 
        label_visibility="collapsed"
    )

# ---------------------------------------------------------
# 4. LOGICA DI VISUALIZZAZIONE
# ---------------------------------------------------------

if selected_view == "🦅 DASHBOARD":
    
    # === A. KAIROS TRADING HUD (GLASSMORPHISM) ===
    acct = st.session_state.broker.get_account_info()
    margin_class = "money" if acct['free_margin'] > 100 else "risk" if acct['free_margin'] > 50 else "danger"
    
    st.markdown(f"""
    <div class="trading-card-container">
        <div class="trading-header" style="display:flex; justify-content:space-between; align-items:center;">
            <span>🛡️ KAIROS TRADING HUD</span>
            <span style="font-size: 12px; opacity: 0.7; font-family: monospace;">ACC: {acct.get('login', 'N/A')}</span>
        </div>
        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-label">💰 Balance</div>
                <div class="metric-value">${acct['balance']:,.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">📈 Equity</div>
                <div class="metric-value money">${acct['equity']:,.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">🔒 Used Margin</div>
                <div class="metric-value">${acct['used_margin']:,.2f}</div>
            </div>
            <div class="metric-box" style="border-color: rgba(255,255,255,0.1);">
                <div class="metric-label">🫁 Free Oxygen</div>
                <div class="metric-value {margin_class}">${acct['free_margin']:,.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_desk_L, col_desk_R = st.columns([1.3, 1.2])

    # --- COLONNA SINISTRA: POSIZIONI & SEGNALI ---
    with col_desk_L:
        st.markdown("""
        <div class="trading-card-container" style="min-height: 420px;">
            <div class="trading-header">
                <span>🚦 LIVE POSITIONS & SIGNALS</span>
            </div>
        """, unsafe_allow_html=True)

        open_positions = st.session_state.broker.get_positions()
        
        if not open_positions:
            st.info("😴 Nessuna posizione aperta.")
        else:
            # Qui potresti chiamare la strategia sui dati in tempo reale se necessario
            traffic_signals = st.session_state.strategy.analyze_portfolio(df) if not df.empty else []
            
            # Mostra posizioni esistenti (mockup visuale basato sui segnali)
            if not traffic_signals:
                st.write("Posizioni aperte presenti (Visualizzazione grezza):")
                st.dataframe(open_positions)
            else:
                for signal in traffic_signals:
                    color_hex = "#2ECC71" if signal['status'] == "GREEN" else "#F59E0B" if signal['status'] == "YELLOW" else "#EF4444"
                    bg_hex = f"{color_hex}15"
                    st.markdown(f"""
                    <div style="background:{bg_hex}; border-left: 4px solid {color_hex}; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:700; color:#FFF; font-size:16px;">{signal['ticker']}</span>
                            <span style="font-size:10px; background:#0F172A; padding:2px 6px; border-radius:4px; color:{color_hex}; border:1px solid {color_hex};">{signal['status']}</span>
                        </div>
                        <div style="font-size:12px; color:#CBD5E1; margin-top:5px;"><i>"{signal['msg']}"</i></div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # --- COLONNA DESTRA: CALCOLATORE DINAMICO (FIX APPLICATO) ---
    # --- COLONNA DESTRA: CALCOLATORE DINAMICO (CORRETTO) ---
    with col_desk_R:
        st.markdown("""
        <div class="trading-card-container" style="min-height: 420px; border-color: rgba(46, 204, 113, 0.3);">
            <div class="trading-header">
                <span>📊 SMART MARGIN CALCULATOR</span>
            </div>
        """, unsafe_allow_html=True)

        # 1. Recupero Lista Asset Disponibili
        live_assets = st.session_state.broker.get_all_available_tickers()
        live_assets.sort()
        
        # 2. Logica Selezione Sicura
        default_index = 0
        current_search = selected_asset_search if selected_asset_search != "TUTTI" else None
        if current_search and current_search in live_assets:
            try:
                default_index = live_assets.index(current_search)
            except ValueError:
                default_index = 0
        
        target_ticker = st.selectbox(
            "Asset Selection", 
            live_assets, 
            index=default_index, 
            key="hud_ticker_select"
        )

        # 3. Recupero Dati Specifica Asset
        specs = st.session_state.broker.get_asset_specs(target_ticker)
        tick_info = st.session_state.broker.get_latest_tick(target_ticker)

        if specs and tick_info:
            # Conversione Timestamp
            last_time = datetime.datetime.fromtimestamp(tick_info['timestamp']).strftime('%H:%M:%S')
            
            # Layout Input: Dividiamo in Size e Prezzo
            c_input_1, c_input_2 = st.columns(2)
            
            # A. INPUT SIZE
            with c_input_1:
                min_lot = specs.get('min_lot', 0.01)
                step_lot = specs.get('step_lot', 0.01)
                selected_size = st.number_input(
                    "Volume (Lots)",
                    min_value=float(min_lot),
                    value=float(min_lot),
                    step=float(step_lot),
                    format="%.2f"
                )

            # B. INPUT ENTRY PRICE (Ripristinato)
            # Permette di modificare il prezzo per simulazioni, defaultando al prezzo attuale
            with c_input_2:
                entry_price = st.number_input(
                    "Entry Price ($)",
                    value=float(tick_info['price']),
                    step=0.01,
                    format="%.2f"
                )
            
            # C. CALCOLO MARGINE SUI DATI INSERITI
            # Valore Nozionale = Prezzo Inserito * Lotti * Dimensione Contratto
            notional = entry_price * selected_size * specs['contract_size']
            
            # Margine = Nozionale / Leva
            leverage = specs.get('leverage', 50.0)
            required_margin = notional / leverage if leverage > 0 else 0
            
            # Impatto % sull'Equity
            impact_pct = (required_margin / acct['equity'] * 100) if acct['equity'] > 0 else 0
            impact_color = "#EF4444" if impact_pct > 50 else "#F59E0B" if impact_pct > 20 else "#2ECC71"

            # D. VISUALIZZAZIONE RISULTATO
            st.markdown(f"""
            <div style="background:rgba(46,204,113,0.05); border:1px solid rgba(46,204,113,0.2); padding:15px; border-radius:10px; text-align:center; margin-top:10px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                     <span style="font-size:9px; color:#64748B;">LAST UPDATE: {last_time}</span>
                     <span style="font-size:9px; color:#64748B;">LEV: 1:{int(leverage)}</span>
                </div>
                <div style="font-size:10px; color:#94A3B8; letter-spacing:1px; margin-bottom:2px;">REQUIRED MARGIN</div>
                <div style="font-size:26px; font-weight:700; color:#2ECC71; font-family:'Space Grotesk', monospace;">${required_margin:,.2f}</div>
                <div style="font-size:11px; color:{impact_color}; margin-top:4px; font-weight:600;">IMPACT: {impact_pct:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
            
            # E. RISK ENGINE CHECK
            st.markdown("---")
            c1, c2 = st.columns([1, 1.5])
            with c1: 
                # Input Stop Loss
                sl_input = st.number_input("Stop Loss ($)", value=0.0, format="%.2f")
            with c2: 
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🧮 VERIFY TRADE", use_container_width=True):
                    # Passiamo l'entry_price manuale al risk engine
                    res = st.session_state.risk_engine.check_trade_feasibility(target_ticker, "LONG", entry_price, sl_input)
                    if res.get('allowed', False): 
                        st.success(f"✅ SIZE OK (Max: {res.get('max_lots', 0)})")
                    else: 
                        st.error(f"❌ {res.get('reason', 'Denied')}")

        else:
            st.warning("Dati asset non disponibili.")

        st.markdown("</div>", unsafe_allow_html=True)

    # === B. FEED CONTENUTI INTELLIGENTI ===
    if not df.empty:
        if selected_asset_search and selected_asset_search != "TUTTI":
            st.markdown(f"### 🔎 Risultati per: <span style='color:#2ECC71'>{selected_asset_search}</span>", unsafe_allow_html=True)
            asset_df = df[df['asset_ticker'] == selected_asset_search].copy()
            if not asset_df.empty:
                # Usa il generatore di card HTML
                cards_html = "".join([_generate_html_card(row) for _, row in asset_df.iterrows()])
                st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
            else:
                st.info("Nessuna news recente per questo asset.")
        else:
            # Vista Default: Carosello + Tutte le sezioni
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