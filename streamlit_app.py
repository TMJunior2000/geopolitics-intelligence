import streamlit as st
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import load_css
from frontend.ui.cards import render_grid

# Configurazione pagina deve essere la PRIMA istruzione Streamlit
st.set_page_config(page_title="Trading Intel 3.0", layout="wide", page_icon="🧠")

# --- CARICAMENTO CSS ESTERNO ---
# Ora gestito in modo sicuro rispetto ai path
load_css("style.css")

@st.cache_data(ttl=300)
def load_data():
    try:
        repo = MarketRepository()
        raw = repo.get_all_insights_flat()
        if not raw: 
            return pd.DataFrame()
        
        df = pd.DataFrame(raw)
        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Errore connessione database: {e}")
        return pd.DataFrame()

df = load_data()

# --- UI HEADER ---
st.markdown("""
<div style="text-align:center; padding: 20px 0;">
    <h1 style="font-family:'Space Grotesk', sans-serif; font-size: 50px; margin:0;">🧠 Trading Intelligence</h1>
    <p style="color:#888; letter-spacing:2px;">AI-POWERED MARKET ANALYSIS TERMINAL</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Nessun dato trovato o database non raggiungibile.")
    st.stop()

# --- FILTRI ---
unique_assets = sorted(df['asset_ticker'].dropna().unique().tolist())
all_assets = ["TUTTI"] + unique_assets

if 'active_filter' not in st.session_state:
    st.session_state.active_filter = "TUTTI"

# Grid dei filtri
buttons_per_row = 8
for row_idx in range(0, len(all_assets), buttons_per_row):
    row_assets = all_assets[row_idx:row_idx + buttons_per_row]
    cols = st.columns(len(row_assets))
    
    for i, asset in enumerate(row_assets):
        with cols[i]:
            is_active = st.session_state.active_filter == asset
            if st.button(asset, key=f"btn_{asset}", 
                        type="primary" if is_active else "secondary",
                        use_container_width=True):
                st.session_state.active_filter = asset
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- RENDER ---
target_list = unique_assets if st.session_state.active_filter == "TUTTI" else [st.session_state.active_filter]
render_grid(df, target_list)

# --- FOOTER ---
st.markdown("---")
f_col1, f_col2 = st.columns([4,1])
with f_col1:
    st.caption(f"📊 {len(df)} insights totali | Ultimo aggiornamento: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}")
with f_col2:
    if st.button("🔄 AGGIORNA DATI", use_container_width=True):
        st.cache_data.clear()
        st.rerun()