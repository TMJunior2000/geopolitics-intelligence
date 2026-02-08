import streamlit as st
from dotenv import load_dotenv
import os

# 1. CARICA LE VARIABILI PRIMA DI TUTTO
load_dotenv()

import pandas as pd
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
    
    # === A. KAIROS TRADING DESK (SEMPRE VISIBILE QUI) ===
    st.markdown("## 🛡️ KAIROS TRADING DESK")

    # 1. VISUALIZZA STATO CONTO
    acct = st.session_state.broker.get_account_info()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Balance", f"${acct['balance']:.2f}")
    c2.metric("📈 Equity", f"${acct['equity']:.2f}")
    c3.metric("🔒 Margin", f"${acct['used_margin']:.2f}")
    surv_color = "normal" if acct['free_margin'] > 50 else "off"
    c4.metric("🫁 Free Oxygen", f"${acct['free_margin']:.2f}", delta_color=surv_color)

    # 2. SEMAFORO POSIZIONI APERTE
    open_positions = st.session_state.broker.get_positions()
    if open_positions:
        st.markdown("### 🚦 Gestione Posizioni Aperte")
        traffic_signals = st.session_state.strategy.analyze_portfolio(df)
        
        if not traffic_signals:
            st.info("Nessuna nuova insight rilevante per le tue posizioni.")
        
        for signal in traffic_signals:
            color = "🟢" if signal['status'] == "GREEN" else "🟡" if signal['status'] == "YELLOW" else "🔴"
            with st.container(border=True):
                col_icon, col_info, col_act = st.columns([1, 4, 2])
                with col_icon: st.markdown(f"# {color}")
                with col_info:
                    st.markdown(f"**{signal['ticker']} ({signal['my_pos']})**")
                    st.caption(f"News: {signal['card_summary']}")
                    st.write(f"**AI Dice:** {signal['msg']}")
                with col_act:
                    if signal['status'] == "RED":
                        st.button(f"CHIUDI {signal['ticker']}", key=f"close_{signal['ticker']}", type="primary")

    # 3. SIMULATORE DI INGRESSO (Risk Engine)
    st.markdown("### ⚡ Smart Entry Calculator")
    with st.container(border=True):
        col_in1, col_in2, col_in3 = st.columns(3)
        # Se c'è una ricerca attiva, pre-selezioniamo quell'asset nel calcolatore
        default_idx = 0
        if selected_asset_search and selected_asset_search != "TUTTI":
            try:
                default_idx = ["NQ100", "BTCUSD", "XAUUSD", "EURUSD"].index(selected_asset_search)
            except:
                pass # Asset non nella lista standard
                
        target_ticker = col_in1.selectbox("Asset", ["NQ100", "BTCUSD", "XAUUSD", "EURUSD"], index=default_idx)
        entry_price = col_in2.number_input("Prezzo Ingresso", value=25000.0)
        stop_loss = col_in3.number_input("Stop Loss", value=25200.0)
        
        if st.button("🧮 CALCOLA SIZE SICURA"):
            direction = "SHORT" if stop_loss > entry_price else "LONG"
            result = st.session_state.risk_engine.check_trade_feasibility(
                target_ticker, direction, entry_price, stop_loss
            )
            
            if result['allowed']:
                st.success("✅ **TRADE APPROVATO DAL RISK MANAGER**")
                st.markdown(f"""
                Per non bruciare il conto (Zero-Ruin), puoi aprire massimo:
                # **{result['max_lots']} Lotti**
                * **Margine Richiesto:** ${result['margin_required']}
                * **Rischio Monetario (SL):** ${result['risk_monetary']}
                * **Equity Residua (Worst Case):** ${result['survival_equity']}
                """)
                st.button(f"Esegui {result['max_lots']} {target_ticker}", type="primary")
            else:
                st.error(f"⛔ **TRADE BLOCCATO**")
                st.warning(result['reason'])
                st.markdown("Il sistema impedisce l'apertura per proteggere il capitale residuo.")

    st.markdown("---")

    # === B. CONTENUTO SOTTOSTANTE (CAROSELLO vs RICERCA) ===
    
    # 1. CASO RICERCA ATTIVA: Mostriamo solo l'asset cercato sotto al desk
    if selected_asset_search and selected_asset_search != "TUTTI":
        
        target_asset = selected_asset_search
        
        # Header Focus Mode
        st.markdown(f"""
        <div style="margin-top: 10px; margin-bottom: 25px; padding: 15px 20px; background: linear-gradient(90deg, rgba(46, 204, 113, 0.1) 0%, transparent 100%); border-left: 4px solid #2ECC71; border-radius: 8px; display:flex; align-items:center; justify-content:space-between;">
            <div>
                <h2 style="margin:0; font-size: 32px; color:#F8FAFC;">{target_asset}</h2>
                <span style="color:#94A3B8; font-size:14px;">Risultati filtrati</span>
            </div>
            <div style="text-align:right;">
                <span style="background:#0F172A; color:#2ECC71; padding:4px 12px; border-radius:6px; font-weight:700; border:1px solid #2ECC71; font-size:10px; letter-spacing:1px;">FOCUS MODE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Filtra dati
        asset_df = df[df['asset_ticker'] == target_asset].copy()
        
        if not asset_df.empty:
            asset_df['sort_date'] = asset_df['published_at'].fillna(asset_df['created_at'])
            asset_df['sort_date'] = pd.to_datetime(asset_df['sort_date'], utc=True)
            asset_df = asset_df.sort_values(by='sort_date', ascending=False)
            
            cards_html = ""
            for _, row in asset_df.iterrows():
                ftype = row.get('feed_type', 'VIDEO')
                c_type = "TRUMP" if ftype == 'SOCIAL_POST' else "VIDEO"
                cards_html += _generate_html_card(row, card_type=c_type)
            
            st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
        else:
            st.info(f"Nessuna informazione trovata per {target_asset}.")

    # 2. CASO STANDARD (NESSUNA RICERCA): Mostriamo tutto
    else:
        render_carousel(df)
        st.markdown("### 📡 Live Intelligence Feed")
        render_all_assets_sections(df)

elif selected_view == "🇺🇸 TRUMP WATCH":
    # Qui se cerchi un asset, potresti voler vedere solo le card di quell'asset legate a Trump
    # Oppure ignorare la ricerca. Per ora lascio la vista standard Trump.
    render_trump_section(df)

elif selected_view == "🧠 MARKET INSIGHTS":
    render_all_assets_sections(df)    

st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)