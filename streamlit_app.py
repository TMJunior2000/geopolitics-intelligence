import streamlit as st
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import load_css
# Importa la funzione _generate_html_card se serve per il rendering personalizzato
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
        if not raw: return pd.DataFrame()
        
        df = pd.DataFrame(raw)
        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)
        
        return df.sort_values(by='published_at', ascending=False)
    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame()

df = load_data()

# ---------------------------------------------------------
# 3. HEADER & NAVIGAZIONE (NUOVO STILE)
# ---------------------------------------------------------

# Header
st.markdown("""
<div style="padding: 20px 0 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;">
    <h1 style="font-size: 42px; letter-spacing: -1px; margin-bottom: 0;">Worldy <span style="color:#2ECC71">Finance</span> AI</h1>
    <p style="color: #94A3B8; font-size: 16px;">Intelligence Platform for Modern Traders</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ In attesa di dati...")
    st.stop()

# --- NAVIGATION BAR (CHIPS) ---
# Estrai ticker unici
all_tickers_raw = df['asset_ticker'].dropna().astype(str).unique().tolist()
all_tickers_clean = sorted([t for t in all_tickers_raw if t.strip() != ''])

# Creiamo le opzioni: La prima è "DASHBOARD" (ex TUTTI), poi gli asset
nav_options = ["🦅 DASHBOARD"] + all_tickers_clean

# Renderizziamo i "Chips" orizzontali
selected_nav = st.radio(
    "Navigazione", 
    options=nav_options, 
    horizontal=True, 
    label_visibility="collapsed" # Nasconde l'etichetta "Navigazione"
)

# Mappiamo la selezione (rimuoviamo l'emoji per il filtro logico)
selected_asset = "TUTTI" if selected_nav == "🦅 DASHBOARD" else selected_nav

# ---------------------------------------------------------
# 4. RENDER SEZIONI (LOGICA)
# ---------------------------------------------------------

if selected_asset == "TUTTI":
    # --- VISTA GENERALE ---
    
    # A. Carosello
    render_carousel(df)

    # B. Sezione Trump
    render_trump_section(df)

    # C. Lista Asset (quella nuova che abbiamo fatto)
    # Mostra i video raggruppati per asset
    render_all_assets_sections(df)

else:
    # --- VISTA FOCUS ASSET ---
    
    st.markdown(f"""
    <div style="margin-top: 20px; margin-bottom: 30px; padding: 20px; background: rgba(46, 204, 113, 0.05); border: 1px solid rgba(46, 204, 113, 0.2); border-radius: 16px; display:flex; align-items:center; gap:15px;">
        <h1 style="margin:0; font-size: 40px; color:#F8FAFC;">{selected_asset}</h1>
        <span style="background:#2ECC71; color:#0F172A; padding:4px 12px; border-radius:6px; font-weight:800; font-size:12px; letter-spacing:1px;">FOCUS MODE</span>
    </div>
    """, unsafe_allow_html=True)

    # Filtra dati
    asset_df = df[df['asset_ticker'] == selected_asset].copy()
    
    if not asset_df.empty:
        # Ordina
        asset_df['sort_date'] = asset_df['published_at'].fillna(asset_df['created_at'])
        asset_df['sort_date'] = pd.to_datetime(asset_df['sort_date'], utc=True)
        asset_df = asset_df.sort_values(by='sort_date', ascending=False)
        
        # Genera Griglia
        cards_html = ""
        for _, row in asset_df.iterrows():
            ftype = row.get('feed_type', 'VIDEO')
            c_type = "TRUMP" if ftype == 'SOCIAL_POST' else "VIDEO"
            cards_html += _generate_html_card(row, card_type=c_type)
        
        st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
    else:
        st.info(f"Nessuna informazione recente trovata per {selected_asset}.")

# Pulsante Refresh Flottante (Opzionale, dato che non c'è più sidebar)
# Mettilo in fondo alla pagina o in alto a destra se serve
st.markdown("---")
if st.button("🔄 Aggiorna Dati Database"):
    st.cache_data.clear()
    st.rerun()