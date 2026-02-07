import streamlit as st
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import render_trump_section, render_carousel, render_all_assets_sections, _generate_html_card, render_market_section

# 1. SETUP & DATI
st.set_page_config(page_title="Trading Intel", layout="wide", page_icon="🦅")
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

# ---------------------------------------------------------
# 3. HEADER & NAVIGAZIONE IBRIDA
# ---------------------------------------------------------

# Titolo
st.markdown("""
<div style="padding: 10px 0 0 0; margin-bottom: 10px;">
    <h1 style="font-size: 38px; letter-spacing: -1px; margin: 0;">Worldy <span style="color:#2ECC71">Finance</span> AI</h1>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Caricamento dati...")
    st.stop()

# --- LAYOUT NAVIGAZIONE (2 Colonne) ---
col_nav, col_search = st.columns([2, 1]) # 2/3 Navigazione, 1/3 Ricerca

# A. Colonna Sinistra: CHIPS (Macro Categorie)
with col_nav:
    # Menu orizzontale
    nav_options = ["🦅 DASHBOARD", "🇺🇸 TRUMP WATCH", "🧠 MARKET INSIGHTS"]
    selected_view = st.radio("Nav", options=nav_options, horizontal=True, label_visibility="collapsed")

# B. Colonna Destra: RICERCA ASSET (Dropdown)
with col_search:
    # Estrai ticker unici
    all_tickers = sorted(df['asset_ticker'].dropna().astype(str).unique().tolist())
    # Aggiungi opzione vuota all'inizio
    search_options = ["🔍 Cerca Asset..."] + [t for t in all_tickers if t.strip()]
    
    selected_asset_search = st.selectbox("Search", options=search_options, label_visibility="collapsed")

# ---------------------------------------------------------
# 4. LOGICA DI VISUALIZZAZIONE ("Chi vince?")
# ---------------------------------------------------------

# CASO A: L'utente ha selezionato un ASSET specifico nella ricerca
if selected_asset_search != "🔍 Cerca Asset...":
    
    target_asset = selected_asset_search
    
    # Header Asset Mode
    st.markdown(f"""
    <div style="margin-top: 10px; margin-bottom: 25px; padding: 15px 20px; background: linear-gradient(90deg, rgba(46, 204, 113, 0.1) 0%, transparent 100%); border-left: 4px solid #2ECC71; border-radius: 8px; display:flex; align-items:center; justify-content:space-between;">
        <div>
            <h2 style="margin:0; font-size: 32px; color:#F8FAFC;">{target_asset}</h2>
            <span style="color:#94A3B8; font-size:14px;">Timeline completa</span>
        </div>
        <div style="text-align:right;">
            <span style="background:#0F172A; color:#2ECC71; padding:4px 12px; border-radius:6px; font-weight:700; border:1px solid #2ECC71;">FOCUS MODE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Filtra e Mostra Cards
    asset_df = df[df['asset_ticker'] == target_asset].copy()
    
    if not asset_df.empty:
        # Ordina per data (unificata)
        asset_df['sort_date'] = asset_df['published_at'].fillna(asset_df['created_at'])
        asset_df = asset_df.sort_values(by='sort_date', ascending=False)
        
        cards_html = ""
        for _, row in asset_df.iterrows():
            ftype = row.get('feed_type', 'VIDEO')
            c_type = "TRUMP" if ftype == 'SOCIAL_POST' else "VIDEO"
            cards_html += _generate_html_card(row, card_type=c_type)
        
        st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
    else:
        st.info(f"Nessuna informazione trovata per {target_asset}.")

# CASO B: Nessuna ricerca, segui la Navigazione (Chips)
else:
    
    if selected_view == "🦅 DASHBOARD":
        # 1. Carosello (Briefing)
        render_carousel(df)
        
        # 2. Separatore Elegante
        st.markdown("---")
        
        # 3. Lista Completa Asset (La funzione nuova che abbiamo fatto)
        render_all_assets_sections(df)

    elif selected_view == "🇺🇸 TRUMP WATCH":
        render_trump_section(df)

    elif selected_view == "🧠 MARKET INSIGHTS":
        render_market_section(df, assets_filter="TUTTI")

# Footer tecnico
st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)