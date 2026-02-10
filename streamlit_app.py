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
    
    # ==============================================================================
    # 0. GLOBAL CSS FIXES (ALLINEAMENTO PIXEL-PERFECT)
    # ==============================================================================
    st.markdown("""
    <style>
        /* --- 1. STILE ETICHETTE "OXYGEN" --- */
        /* Targettiamo il testo p dentro le label dei widget orizzontali */
        div[data-testid="stHorizontalBlock"] [data-testid="stWidgetLabel"] p {
            font-size: 10px !important;
            color: #94A3B8 !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            font-family: 'Inter', sans-serif !important;
            margin-bottom: 0px !important;
        }
        
        /* Forza altezza minima uguale per tutte le label (allinea Selectbox e Input) */
        div[data-testid="stHorizontalBlock"] [data-testid="stWidgetLabel"] {
            min-height: 20px !important;
            margin-bottom: 5px !important;
            display: flex !important;
            align-items: end !important; /* Allinea il testo in basso */
        }

        /* --- 2. ALTEZZE INPUT UNIFORMI --- */
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-testid="stNumberInput"] div[data-baseweb="input"],
        div[data-testid="stNumberInput"] input {
            height: 42px !important;
            min-height: 42px !important;
            border-radius: 8px !important;
        }

        /* --- 3. FIX ALLINEAMENTO BOTTONE VERIFY --- */
        /* Aggiunge margine sopra il bottone pari all'altezza della label + gap */
        div[data-testid="stHorizontalBlock"] button[kind="primary"] {
            height: 42px !important;
            min-height: 42px !important;
            border-radius: 8px !important;
            margin-top: 25px !important; /* <--- QUESTO LO ALLINEA PERFETTAMENTE */
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }

        /* Container HUD */
        .hud-container { 
            border: 1px solid rgba(46, 204, 113, 0.2); 
            border-radius: 12px; 
            overflow: hidden; 
            margin-bottom: 25px; 
            background: rgba(15, 23, 42, 0.6); 
            backdrop-filter: blur(20px); 
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5); 
        }
    </style>
    """, unsafe_allow_html=True)

    # ==============================================================================
    # 1. ZONE: KAIROS HUD (HTML Piatto)
    # ==============================================================================
    acct = st.session_state.broker.get_account_info()
    margin_class = "money" if acct['free_margin'] > 100 else "risk" if acct['free_margin'] > 50 else "danger"
    open_positions = st.session_state.broker.get_positions()
    
    # HEADER
    oxy_color = '#EF4444' if margin_class == 'danger' else '#F8FAFC'
    html_header = (
        f'<div style="background: rgba(15, 23, 42, 0.9); padding: 15px 20px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: space-between;">'
        f'<div style="display:flex; align-items:center;">'
        f'<span style="font-size: 10px; color: #94A3B8; margin-right: 6px; font-weight: 700; letter-spacing: 1px;">BALANCE</span>'
        f'<span style="font-family: \'Space Grotesk\'; font-weight: 700; color: #F8FAFC; font-size: 18px; margin-right: 20px;">${acct["balance"]:,.2f}</span>'
        f'<span style="border-left:1px solid #334155; height:16px; margin:0 15px;"></span>'
        f'<span style="font-size: 10px; color: #94A3B8; margin-right: 6px; font-weight: 700; letter-spacing: 1px;">EQUITY</span>'
        f'<span style="font-family: \'Space Grotesk\'; font-weight: 700; color: #2ECC71; font-size: 18px; margin-right: 20px; text-shadow: 0 0 15px rgba(46,204,113,0.2);">${acct["equity"]:,.2f}</span>'
        f'<span style="border-left:1px solid #334155; height:16px; margin:0 15px;"></span>'
        f'<span style="font-size: 10px; color: #94A3B8; margin-right: 6px; font-weight: 700; letter-spacing: 1px;">OXYGEN</span>'
        f'<span style="font-family: \'Space Grotesk\'; font-weight: 700; font-size: 18px; color: {oxy_color}">${acct["free_margin"]:,.0f}</span>'
        f'</div>'
        f'<div><span style="font-family: monospace; font-size: 11px; color: #475569; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px;">ID: {acct.get("login", "N/A")}</span></div>'
        f'</div>'
    )

    # BODY
    html_body = ""
    if not open_positions:
        html_body = (
            '<div style="padding: 15px 20px; background: rgba(2, 6, 23, 0.4); min-height: 50px; display: flex; align-items: center;">'
            '<div style="color: #64748B; font-size: 13px; display: flex; align-items: center; font-style: italic;">'
            '<span style="font-size: 18px; margin-right: 10px; opacity: 0.7;">💤</span>'
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
                f'<div style="border-left: 3px solid {color}; background: linear-gradient(90deg, {bg_color} 0%, rgba(0,0,0,0) 100%); padding: 8px 12px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05); min-width: 140px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">'
                f'<span style="font-weight:700; font-size:13px; color: #F1F5F9;">{pos["symbol"]}</span>'
                f'<span style="font-size:9px; background:rgba(255,255,255,0.1); padding:1px 4px; border-radius:3px; color:#CBD5E1;">{pos["type"]}</span>'
                f'</div>'
                f'<div style="font-size:14px; font-family:monospace; font-weight:700; color: {pnl_color};">{pos["profit"]:+.2f} $</div>'
                f'</div>'
            )
        html_body = f'<div style="padding: 15px 20px; background: rgba(2, 6, 23, 0.4); display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">{cards}</div>'

    st.markdown(f'<div class="hud-container">{html_header}{html_body}</div>', unsafe_allow_html=True)

    # ==============================================================================
    # 2. ZONE: EXECUTION BAR (ALLINEAMENTO FIX)
    # ==============================================================================
    
    st.markdown("""
    <div class="hud-container" style="padding: 20px; background: rgba(15, 23, 42, 0.6);">
        <div style="display:flex; align-items:center; margin-bottom: 20px;">
            <span style="color:#F59E0B; margin-right: 10px; font-size: 18px;">⚡</span>
            <span style="font-family:'Space Grotesk'; font-weight:700; color:#F8FAFC; font-size:16px; letter-spacing: 0.5px;">EXECUTION DECK</span>
        </div>
    """, unsafe_allow_html=True)

    live_assets = st.session_state.broker.get_all_available_tickers()
    live_assets.sort()
    
    default_index = 0
    if selected_asset_search and selected_asset_search != "TUTTI" and selected_asset_search in live_assets:
        default_index = live_assets.index(selected_asset_search)
    
    # ----------------------------------------------------------------------
    # FIX LAYOUT COLONNE
    # ----------------------------------------------------------------------
    c1, c2, c3, c4, c5, c6 = st.columns([1.8, 0.8, 1, 1, 1, 1.2], gap="small")
    
    specs = None
    tick_info = None
    
    with c1:
        # ASSET
        target_ticker = st.selectbox("ASSET", live_assets, index=default_index)
        if target_ticker:
            specs = st.session_state.broker.get_asset_specs(target_ticker)
            tick_info = st.session_state.broker.get_latest_tick(target_ticker)
    
    current_price = float(tick_info['price']) if tick_info else 0.0
    
    with c2:
        min_l = float(specs['min_lot']) if specs else 0.01
        step_l = float(specs.get('step_lot', 0.01)) if specs else 0.01
        selected_size = st.number_input("SIZE (LOTS)", min_value=min_l, value=min_l, step=step_l, format="%.2f")
    
    with c3:
        entry_price = st.number_input("ENTRY PRICE", value=current_price, step=0.01, format="%.2f")
        
    with c4:
        sl_val = entry_price * 0.99
        sl_input = st.number_input("STOP LOSS", value=sl_val, format="%.2f")
        
    with c5:
        tp_val = entry_price * 1.02
        tp_input = st.number_input("TAKE PROFIT", value=tp_val, format="%.2f")

    # [CALCOLI DI BACKEND QUI - Invariati...]
    risk_msg, profit_msg, margin_req, leva_str = "N/A", "N/A", 0.0, "N/A"
    if specs:
        contract = specs['contract_size']
        lev = specs.get('leverage', 50)
        leva_str = f"1:{lev:.0f}"
        notional = entry_price * selected_size * contract
        margin_req = notional / lev if lev else 0
        dist_sl = entry_price - sl_input
        money_sl = abs(dist_sl) * selected_size * contract
        pct_sl = (abs(dist_sl)/entry_price)*100 if entry_price else 0
        dist_tp = tp_input - entry_price
        money_tp = abs(dist_tp) * selected_size * contract
        rr = money_tp / money_sl if money_sl > 0 else 0
        risk_color = "#EF4444" if money_sl > (acct['equity']*0.02) else "#94A3B8"
        risk_msg = f"<span style='color:{risk_color}'>-${money_sl:.1f} ({pct_sl:.1f}%)</span>"
        profit_msg = f"<span style='color:#2ECC71'>+${money_tp:.1f} (R:{rr:.1f})</span>"

    with c6:
        # BOTTONE PULITO (L'allineamento è gestito dal CSS margin-top: 25px)
        if st.button("VERIFY", type="primary", use_container_width=True):
            check = st.session_state.risk_engine.check_trade_feasibility(target_ticker, "LONG", entry_price, sl_input)
            if check['allowed']:
                st.toast(f"✅ Trade SAFE! Max Lots: {check['max_lots']}", icon="🛡️")
            else:
                st.toast(f"❌ REJECTED: {check['reason']}", icon="💀")

    st.markdown(f"""
        <div style="display:flex; justify-content: space-between; align-items: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.05); font-size: 11px; font-family: monospace; color: #64748B;">
            <div>MARGIN: <span style="color: #F8FAFC; font-weight:700;">${margin_req:.2f}</span></div>
            <div>RISK: {risk_msg}</div>
            <div>TARGET: {profit_msg}</div>
            <div style="color: #F59E0B; font-weight:700;">LEVA: {leva_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ==============================================================================
    # 3. ZONE: INTELLIGENCE FEED
    # ==============================================================================
    if not df.empty:
        st.markdown(f"""
        <div style="margin-top: 40px; margin-bottom: 20px; display:flex; align-items:center;">
            <span style="font-size:20px; margin-right:10px;">🔥</span>
            <h3 style="margin:0; font-size: 22px;">Daily Briefing <span style="font-size: 14px; color: #64748B; font-weight: 400; margin-left: 10px;">{pd.Timestamp.now().strftime('%d %B')}</span></h3>
        </div>
        """, unsafe_allow_html=True)

        if selected_asset_search and selected_asset_search != "TUTTI":
            asset_df = df[df['asset_ticker'] == selected_asset_search].copy()
            if not asset_df.empty:
                cards_html = "".join([_generate_html_card(row) for _, row in asset_df.iterrows()])
                st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
            else:
                st.info(f"Nessuna news recente per {selected_asset_search}.")
        else:
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