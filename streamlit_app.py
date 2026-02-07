import streamlit as st
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import render_trump_section, render_market_section, render_carousel

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

# ... (CODICE PRECEDENTE: IMPORTS, SETUP, LOAD_DATA rimane uguale) ...

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

# ---------------------------------------------------------
# 4. SIDEBAR FILTRI (AGGIORNATA)
# ---------------------------------------------------------
with st.sidebar:
    st.header("🔍 Filtri")
    
    # 1. Estrai TUTTI i ticker unici (Video + Trump)
    # Puliamo i dati per evitare errori se asset_ticker è nullo
    all_tickers_raw = df['asset_ticker'].dropna().astype(str).unique().tolist()
    all_tickers_clean = sorted([t for t in all_tickers_raw if t.strip() != ''])
    
    # Opzioni menu
    all_options = ["TUTTI"] + all_tickers_clean
    
    selected_asset = st.selectbox("Asset Class", options=all_options)
    
    st.markdown("---")
    st.caption(f"Asset monitorati: {len(all_tickers_clean)}")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# 5. RENDER SEZIONI (LOGICA CONDIZIONALE)
# ---------------------------------------------------------

from frontend.ui.cards import _generate_html_card, render_carousel, render_trump_section, render_market_section

# MODALITÀ DASHBOARD COMPLETA ("TUTTI")
if selected_asset == "TUTTI":
    
    # A. CAROSELLO (Daily Briefing)
    render_carousel(df)

    # B. SEZIONE TRUMP (Feed Social)
    render_trump_section(df)

    # C. SEZIONE VIDEO (Analisi Mercato)
    render_market_section(df, assets_filter="TUTTI")

# MODALITÀ ASSET SPECIFICO (Timeline dedicata)
else:
    # 1. Intestazione Asset
    st.markdown(f"""
    <div style="margin-bottom: 20px; display:flex; align-items:center; gap:10px;">
        <h2 style="margin:0;">Focus: <span style="color:#3B82F6">{selected_asset}</span></h2>
        <span style="background:rgba(59, 130, 246, 0.2); color:#3B82F6; padding:2px 8px; border-radius:4px; font-size:12px; border:1px solid #3B82F6;">TIMELINE</span>
    </div>
    """, unsafe_allow_html=True)

    # 2. Filtra il DataFrame per l'asset selezionato
    asset_df = df[df['asset_ticker'] == selected_asset].copy()
    
    if not asset_df.empty:
        # Crea la colonna data unificata per ordinamento
        asset_df['sort_date'] = asset_df['published_at'].fillna(asset_df['created_at'])
        asset_df['sort_date'] = pd.to_datetime(asset_df['sort_date'], utc=True)
        
        # Ordina dal più recente
        asset_df = asset_df.sort_values(by='sort_date', ascending=False)
        
        # 3. Genera la Griglia
        cards_html = ""
        for _, row in asset_df.iterrows():
            # Determina il tipo
            ftype = row.get('feed_type', 'VIDEO')
            c_type = "TRUMP" if ftype == 'SOCIAL_POST' else "VIDEO"
            
            # Genera la card (usa la tua funzione _generate_html_card esistente)
            cards_html += _generate_html_card(row, card_type=c_type)
        
        # Renderizza
        st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
        
    else:
        st.info(f"Nessuna informazione recente trovata per {selected_asset}.")