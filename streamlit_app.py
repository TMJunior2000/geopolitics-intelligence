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
    
    # Calcolo classi CSS dinamiche per i colori
    margin_class = "money" if acct['free_margin'] > 100 else "risk" if acct['free_margin'] > 50 else "danger"
    
    # 1. VISUALIZZA STATO CONTO (HTML CUSTOM PER MATCHARE LO STILE)
    st.markdown(f"""
    <div class="trading-card-container">
        <div class="trading-header">
            <span>🛡️ KAIROS TRADING HUD</span>
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

    # 3. SIMULATORE DI INGRESSO (COLONNA DESTRA - MODIFICATA PER FP MARKETS + PREZZO LIVE)
    with col_desk_R:
        # Wrapper grafico inizio
        st.markdown("""
        <div class="trading-card-container" style="min-height: 380px; border-color: rgba(241, 196, 15, 0.2);">
            <div class="trading-header">
                <span>⚡ SMART ENTRY</span>
            </div>
        """, unsafe_allow_html=True)

        # 1. Recupera Asset dal Broker
        live_assets = st.session_state.broker.get_all_available_tickers()
        live_assets.sort() 

        # Logica di Pre-selezione
        default_idx = 0
        if selected_asset_search and selected_asset_search in live_assets:
            default_idx = live_assets.index(selected_asset_search)
        elif "EURUSD" in live_assets:
            default_idx = live_assets.index("EURUSD")

        target_ticker = st.selectbox("Asset Target", live_assets, index=default_idx)
        
        # 2. RECUPERA DATI LIVE (Prezzo, Leva e Min Lot)
        specs = st.session_state.broker.get_asset_specs(target_ticker)
        tick_info = st.session_state.broker.get_latest_tick(target_ticker)
        
        caption_parts = []
        if specs:
            caption_parts.append(f"Leva: 1:{int(specs['leverage'])}")
            caption_parts.append(f"Min: {specs.get('min_lot', 0.01)}")
        
        current_price = 0.0
        if tick_info:
            current_price = tick_info['price']
            
            # --- FIX TIMEZONE (Broker -> Italia) ---
            # I server MT5 sono solitamente GMT+2/GMT+3. L'Italia è GMT+1.
            # Differenza media: 1 o 2 ore avanti. FP Markets è spesso +2 ore rispetto all'Italia.
            # Prendiamo il timestamp grezzo
            tick_ts = tick_info['timestamp']
            
            # Creiamo l'oggetto data base
            dt_obj = datetime.datetime.fromtimestamp(tick_ts)
            
            # SOTTRAIAMO 2 ORE per allinearlo all'Italia (Hack pratico)
            # Se vedi che è ancora sbagliato di 1 ora, cambia in hours=1
            dt_obj_ita = dt_obj - datetime.timedelta(hours=2)
            
            time_str = dt_obj_ita.strftime('%d/%m %H:%M:%S')
            
            caption_parts.append(f"🔴 {current_price} ({time_str})")
        
        st.caption(" | ".join(caption_parts))

        # 3. INPUT PREZZI (Pre-compilati con il prezzo attuale)
        c2a, c2b = st.columns(2)
        
        # Se abbiamo il prezzo live, lo usiamo come default nel box
        default_entry = float(current_price) if current_price > 0 else 0.0
        
        # Formattazione intelligente
        fmt = "%.5f" if "USD" in target_ticker and "BTC" not in target_ticker and "NQ" not in target_ticker else "%.2f"

        with c2a: 
            entry_input = st.number_input("Entry Price", value=default_entry, step=0.01, format=fmt)
        with c2b: 
            stop_input = st.number_input("Stop Loss", value=0.0, step=0.01, format=fmt)
        
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        
        # 4. CALCOLO
        if st.button("🧮 CALCOLA SIZE SICURA", type="primary", use_container_width=True):
            if entry_input > 0 and stop_input > 0:
                direction = "SHORT" if stop_input > entry_input else "LONG"
                
                # Chiama il Risk Engine (Userà la leva corretta di FP Markets)
                result = st.session_state.risk_engine.check_trade_feasibility(
                    target_ticker, direction, entry_input, stop_input
                )
                
                st.markdown("---")
                if result['allowed']:
                    # Risultato formattato stile "Ticket"
                    st.markdown(f"""
                    <div style="text-align:center;">
                        <div style="font-size:10px; color:#94A3B8; letter-spacing:1px;">SIZE CONSIGLIATA</div>
                        <div style="font-size:32px; font-weight:700; color:#2ECC71; font-family:'Space Grotesk'; text-shadow:0 0 15px rgba(46,204,113,0.3);">{result['max_lots']} LOTS</div>
                        <div style="display:flex; justify-content:space-between; margin-top:10px; font-size:11px; color:#CBD5E1;">
                            <span>Risk: <b>${result['risk_monetary']}</b></span>
                            <span>Margin: <b>${result['margin_required']}</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    st.button(f"APRI {direction} {target_ticker}", use_container_width=True)
                else:
                    st.markdown(f"""
                    <div style="text-align:center; padding:10px; background:rgba(239, 68, 68, 0.1); border-radius:8px; border:1px solid rgba(239, 68, 68, 0.3);">
                        <div style="color:#EF4444; font-weight:700;">⛔ TRADE BLOCCATO</div>
                        <div style="font-size:11px; color:#FCA5A5; margin-top:5px;">{result['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("Inserisci Prezzo e Stop Loss validi.")
        
        # Wrapper grafico fine
        st.markdown("</div>", unsafe_allow_html=True)


    # === B. CONTENUTO SOTTOSTANTE (CAROSELLO vs RICERCA) ===
    # ... (Il resto del codice sotto rimane uguale a prima) ...
    # 1. CASO RICERCA ATTIVA...
    if selected_asset_search and selected_asset_search != "TUTTI":
        # ... codice ricerca ...
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

    # 2. CASO STANDARD
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