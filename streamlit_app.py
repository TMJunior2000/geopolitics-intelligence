import streamlit as st
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import render_trump_section, render_market_section

# 1. SETUP PAGINA
st.set_page_config(page_title="Trading Intel", layout="wide", page_icon="🦅")
load_css("style.css")

# 2. CARICAMENTO DATI
@st.cache_data(ttl=300)
def load_data():
    try:
        repo = MarketRepository()
        raw = repo.get_all_insights_flat()
        if not raw: 
            return pd.DataFrame()
        
        df = pd.DataFrame(raw)

        # Converti le date in UTC direttamente
        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
        if 'created_at' in df.columns:  # Per i Trump post
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)
        
        # Ordina per published_at decrescente
        return df.sort_values(by='published_at', ascending=False)

    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame()

df = load_data()

# 3. HEADER (Stile Minimal Worldy)
st.markdown("""
<div style="padding: 20px 0; border-bottom: 1px solid #2D3748; margin-bottom: 30px;">
    <h1 style="font-size: 42px; letter-spacing: -1px; margin-bottom: 0;">Worldy <span style="color:#2ECC71">Finance</span> AI</h1>
    <p style="color: #94A3B8; font-size: 16px;">Intelligence Platform for Modern Traders</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ In attesa di dati...")
    st.stop()

# 4. SIDEBAR FILTRI
with st.sidebar:
    st.header("🔍 Filtri")
    
    # Estrai ticker unici solo dai VIDEO (non da Trump)
    video_assets = sorted(df[df['feed_type'] == 'VIDEO']['asset_ticker'].dropna().unique().tolist())
    all_options = ["TUTTI"] + video_assets
    
    selected_asset = st.selectbox("Asset Class", options=all_options)
    
    st.markdown("---")
    st.caption("v2.0.1 - Worldy UI")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# 5. RENDER SEZIONI
# A. CAROSELLO
if not df.empty:
    # --- Assicuriamoci che le date siano in UTC e convertite in locale ---
    df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
    df['published_local'] = df['published_at'].dt.tz_convert('Europe/Rome')
    
    # --- Trova l'ultimo giorno con dati disponibili ---
    if not df['published_local'].empty:
        latest_day = df['published_local'].dt.date.max()
        
        # Filtra tutte le righe di quel giorno
        today_df = df[df['published_local'].dt.date == latest_day]
        
        if not today_df.empty:
            st.markdown(f"<h2>🔥 Carosello del giorno {latest_day.strftime('%d %b %Y')}</h2>", unsafe_allow_html=True)
            render_market_section(today_df, assets_filter="TUTTI")
            render_trump_section(today_df)
        else:
            st.warning("⚠️ Nessun dato disponibile per l'ultimo giorno con post")


# B. SEZIONE TRUMP
render_trump_section(df if selected_asset=="TUTTI" else df[df['asset_ticker']==selected_asset])

# C. SEZIONE VIDEO
render_market_section(df, selected_asset)