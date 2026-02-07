import streamlit as st
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import render_trump_section, render_carousel, render_all_assets_sections, _generate_html_card

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
    st.markdown('<div style="text-align: center; margin-bottom: 20px;"><h2 style="margin:0;">🦅 RADAR</h2></div>', unsafe_allow_html=True)
    
    # Estrai ticker unici TOTALI per il filtro
    all_tickers_raw = df['asset_ticker'].dropna().astype(str).unique().tolist()
    all_tickers_clean = sorted([t for t in all_tickers_raw if t.strip() != ''])
    all_options = ["TUTTI"] + all_tickers_clean
    
    selected_asset = st.selectbox("Seleziona Asset", options=all_options)
    
    st.markdown("---")
    st.caption("Pannello di Controllo")
    if st.button("🔄 Aggiorna Feed"):
        st.cache_data.clear()
        st.rerun()

# 5. RENDER SEZIONI

if selected_asset == "TUTTI":
    # A. CAROSELLO (Daily Briefing Unificato)
    render_carousel(df)

    # B. SEZIONE TRUMP (Feed Social)
    render_trump_section(df)

    # C. SEZIONE ASSET (Divisa per Ticker)
    # Invece di "render_market_section" generico, usiamo quello nuovo dettagliato
    render_all_assets_sections(df)

else:
    # MODALITÀ FOCUS SU SINGOLO ASSET
    st.markdown(f"""
    <div style="margin-bottom: 30px; display:flex; align-items:center; gap:15px;">
        <h1 style="margin:0; font-size: 50px;">{selected_asset}</h1>
        <span style="background:rgba(46, 204, 113, 0.15); color:#2ECC71; padding:5px 15px; border-radius:8px; font-weight:bold; border:1px solid rgba(46, 204, 113, 0.3);">FOCUS MODE</span>
    </div>
    """, unsafe_allow_html=True)

    # Filtra il DataFrame per l'asset selezionato
    asset_df = df[df['asset_ticker'] == selected_asset].copy()
    
    if not asset_df.empty:
        # Ordina dal più recente
        # Creiamo colonna temporanea sicura per ordinare
        asset_df['sort_date'] = asset_df['published_at'].fillna(asset_df['created_at'])
        asset_df['sort_date'] = pd.to_datetime(asset_df['sort_date'], utc=True)
        asset_df = asset_df.sort_values(by='sort_date', ascending=False)
        
        cards_html = ""
        for _, row in asset_df.iterrows():
            # Determina il tipo
            ftype = row.get('feed_type', 'VIDEO')
            c_type = "TRUMP" if ftype == 'SOCIAL_POST' else "VIDEO"
            cards_html += _generate_html_card(row, card_type=c_type)
        
        st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
    else:
        st.info(f"Nessuna informazione trovata per {selected_asset}.")