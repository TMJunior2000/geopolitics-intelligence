import streamlit as st
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import render_trump_section, render_carousel, render_all_assets_sections, _generate_html_card, render_market_section
from backend.broker import TradingAccount
from backend.risk_engine import SurvivalRiskEngine
from backend.strategy import TrafficLightSystem

# 1. SETUP & DATI
st.set_page_config(page_title="Market Intelligence AI", page_icon="🦅", layout="wide")
load_css("style.css")

@st.cache_data(ttl=300)
def load_data():
    try:
        repo = MarketRepository()
        raw = repo.get_all_insights_flat()
        if not raw: return pd.DataFrame()
        df = pd.DataFrame(raw)
        # Conversione date
        for col in ['published_at', 'created_at']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
        return df.sort_values(by='published_at', ascending=False)
    except Exception as e:
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
col_nav, col_search = st.columns([2.2, 1]) # Un po' più spazio ai bottoni

# A. Colonna Sinistra: CHIPS (Stile W-Badge)
with col_nav:
    # Menu orizzontale
    nav_options = ["🦅 DASHBOARD", "🇺🇸 TRUMP WATCH", "🧠 MARKET INSIGHTS"]
    selected_view = st.radio("Nav", options=nav_options, horizontal=True, label_visibility="collapsed")

# B. Colonna Destra: RICERCA ASSET (Dropdown Intelligente)
with col_search:
    # Estrai ticker unici e pulisci
    all_tickers = sorted(df['asset_ticker'].dropna().astype(str).unique().tolist())
    clean_tickers = [t for t in all_tickers if t.strip()]
    
    # Lista opzioni con "TUTTI" in cima
    search_options = ["TUTTI"] + clean_tickers
    
    # Selectbox con Placeholder "Cerca Asset..."
    # index=None fa sì che all'inizio non ci sia nulla selezionato (mostra placeholder)
    # Quando clicchi, il placeholder sparisce e puoi scrivere
    selected_asset_search = st.selectbox(
        "Search", 
        options=search_options, 
        index=None, 
        placeholder="🔍 Cerca Asset...", 
        label_visibility="collapsed"
    )

# ---------------------------------------------------------
# 4. LOGICA DI VISUALIZZAZIONE ("Chi vince?")
# ---------------------------------------------------------

# Logica: Se l'utente seleziona qualcosa nella ricerca (e non è None), usiamo quello.
# Se seleziona "TUTTI" o lascia vuoto (None), usiamo la navigazione a bottoni.

if selected_asset_search and selected_asset_search != "TUTTI":
    
    # --- MODALITÀ ASSET ---
    target_asset = selected_asset_search
    
    # Header Asset Mode
    st.markdown(f"""
    <div style="margin-top: 10px; margin-bottom: 25px; padding: 15px 20px; background: linear-gradient(90deg, rgba(46, 204, 113, 0.1) 0%, transparent 100%); border-left: 4px solid #2ECC71; border-radius: 8px; display:flex; align-items:center; justify-content:space-between;">
        <div>
            <h2 style="margin:0; font-size: 32px; color:#F8FAFC;">{target_asset}</h2>
            <span style="color:#94A3B8; font-size:14px;">Timeline completa</span>
        </div>
        <div style="text-align:right;">
            <span style="background:#0F172A; color:#2ECC71; padding:4px 12px; border-radius:6px; font-weight:700; border:1px solid #2ECC71; font-size:10px; letter-spacing:1px;">FOCUS MODE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Filtra e Mostra Cards
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

else:
    # --- MODALITÀ NAVIGAZIONE (DASHBOARD / TRUMP / MARKET) ---
    
    if selected_view == "🦅 DASHBOARD":
        render_carousel(df)
        st.markdown("---")
        st.markdown("## 🛡️ KAIROS TRADING DESK")

        # 1. VISUALIZZA STATO CONTO
        acct = st.session_state.broker.get_account_info()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Balance", f"${acct['balance']:.2f}")
        c2.metric("📈 Equity", f"${acct['equity']:.2f}")
        c3.metric("🔒 Margin", f"${acct['used_margin']:.2f}")
        # Colore dinamico per lo spazio vitale
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
            # Simuliamo che l'utente clicchi su una card, qui mettiamo input manuali per test
            col_in1, col_in2, col_in3 = st.columns(3)
            target_ticker = col_in1.selectbox("Asset", ["NQ100", "BTCUSD", "XAUUSD", "EURUSD"])
            entry_price = col_in2.number_input("Prezzo Ingresso", value=25000.0)
            stop_loss = col_in3.number_input("Stop Loss", value=25200.0)
            
            if st.button("🧮 CALCOLA SIZE SICURA"):
                # Determina direzione
                direction = "SHORT" if stop_loss > entry_price else "LONG"
                
                # Chiama il Risk Engine
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
        render_all_assets_sections(df)

    elif selected_view == "🇺🇸 TRUMP WATCH":
        render_trump_section(df)

    elif selected_view == "🧠 MARKET INSIGHTS":
        render_all_assets_sections(df)    
    
st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)