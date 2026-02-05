import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import render_trump_section, render_market_section, render_todays_briefing

# 1. SETUP PAGINA
st.set_page_config(page_title="Trading Intel 3.0", layout="wide", page_icon="🧠")
load_css("style.css")

# 2. CARICAMENTO DATI
@st.cache_data(ttl=300)
def load_data():
    try:
        repo = MarketRepository()
        raw = repo.get_all_insights_flat()
        if not raw: return pd.DataFrame()
        
        df = pd.DataFrame(raw)
        # Converti date
        cols_date = ['published_at', 'created_at']
        for c in cols_date:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')
        
        # Ordina per data (più recente in alto)
        return df.sort_values(by='published_at', ascending=False)
    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame()

df = load_data()

# 3. HEADER
st.markdown("""
<div style="padding: 20px 0; border-bottom: 1px solid #2D3748; margin-bottom: 30px;">
    <h1 style="font-size: 42px; letter-spacing: -1px; margin-bottom: 0;">Worldy <span style="color:#2ECC71">Finance</span> AI</h1>
    <p style="color: #94A3B8; font-size: 16px;">Intelligence Platform for Modern Traders</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ In attesa di dati...")
    st.stop()

# --- GESTIONE TEMPORALE (Settimana Corrente + Storico) ---
if 'history_weeks' not in st.session_state:
    st.session_state.history_weeks = 0 # 0 = Solo settimana corrente

# Calcolo date (Tutto "Naive", senza timezone)
today = pd.Timestamp.now().normalize()
# Troviamo il Lunedì della settimana corrente
start_of_current_week = today - pd.Timedelta(days=today.dayofweek) 
# Data di taglio (che si sposta indietro se premiamo "Carica Storico")
cutoff_date = start_of_current_week - pd.Timedelta(weeks=st.session_state.history_weeks)

# FILTRI DATI
# Dati di OGGI per il Briefing
df_today = df[pd.to_datetime(df['ref_date']).dt.normalize() == today]
# Dati GENERALI filtrati dalla data di taglio in poi
df_view = df[pd.to_datetime(df['ref_date']) >= cutoff_date]

# 4. SIDEBAR FILTRI
with st.sidebar:
    st.header("🔍 Filtri")
    
    # Estrai ticker unici solo dai VIDEO (non da Trump) per il menu
    video_assets = sorted(df[df['feed_type'] == 'VIDEO']['asset_ticker'].dropna().unique().tolist())
    all_options = ["TUTTI"] + video_assets
    
    selected_asset = st.selectbox("Asset Class", options=all_options)
    
    st.divider()
    
    # Pulsante Reset Storico
    if st.session_state.history_weeks > 0:
        st.caption("⚠️ Visualizzazione estesa attiva")
        if st.button("Reimposta a Settimana Corrente"):
            st.session_state.history_weeks = 0
            st.rerun()
    
    st.caption(f"📅 Dati dal: {cutoff_date.strftime('%d/%m/%Y')}")
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# 5. SEZIONE 1: ANTEPRIMA OGGI (Sempre in cima, se ci sono dati)
if not df_today.empty:
    st.markdown("### ☀️ Today's Briefing")
    render_todays_briefing(df_today)
    st.markdown("---")

# 6. SEZIONE 2: TRUMP WATCH (Filtrato per data di taglio)
render_trump_section(df_view)

# 7. SEZIONE 3: MARKET INSIGHTS (Diviso per Asset, filtrato per data)
render_market_section(df_view, selected_asset)

# 8. PULSANTE "CARICA STORICO" (Footer)
st.markdown("<br><br>", unsafe_allow_html=True)
col_load, _ = st.columns([1, 4])
with col_load:
    # Pulsante per caricare una settimana in più
    if st.button("📂 Carica Settimana Precedente", use_container_width=True):
        st.session_state.history_weeks += 1
        st.rerun()