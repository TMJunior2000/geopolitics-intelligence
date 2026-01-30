import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import GLOBAL_STYLES, CARD_CSS
from frontend.ui.cards import generate_grid_html

st.set_page_config(page_title="Trading Intel 3.0", layout="wide", page_icon="🧠")
st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

@st.cache_data(ttl=60) # Refresh veloce per test
def load_data():
    repo = MarketRepository()
    raw = repo.get_all_insights_flat()
    if not raw: return pd.DataFrame()
    df = pd.DataFrame(raw)
    if 'published_at' in df.columns:
        df['published_at'] = pd.to_datetime(df['published_at'])
    return df

df = load_data()

# --- UI HEADER ---
st.markdown("""
<div style="text-align:center; padding: 20px 0;">
    <h1 style="font-family:'Space Grotesk'; font-size: 50px; margin:0;">🧠 Trading Intelligence</h1>
    <p style="color:#888; letter-spacing:2px;">AI-POWERED MARKET ANALYSIS TERMINAL</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Nessun dato trovato nel database.")
    st.stop()

# --- FILTRI ---
unique_assets = sorted(df['asset_ticker'].unique().tolist())
all_assets = ["TUTTI"] + unique_assets

if 'active_filter' not in st.session_state:
    st.session_state.active_filter = "TUTTI"

cols = st.columns(8)
for i, asset in enumerate(all_assets):
    with cols[i % 8]:
        is_active = st.session_state.active_filter == asset
        if st.button(asset, key=f"btn_{asset}", type="primary" if is_active else "secondary"):
            st.session_state.active_filter = asset
            st.rerun()

# --- RENDER ---
target_list = unique_assets if st.session_state.active_filter == "TUTTI" else [st.session_state.active_filter]
html_cards = generate_grid_html(df, target_list)

# Calcolo altezza dinamica approssimativa
num_cards = len(df[df['asset_ticker'].isin(target_list)])
rows = (num_cards // 3) + 1
dynamic_height = max(800, rows * 550)

components.html(
    f"<html><head>{CARD_CSS}</head><body>{html_cards}</body></html>",
    height=dynamic_height, 
    scrolling=True
)

# --- FOOTER ---
st.markdown("---")
f_col1, f_col2 = st.columns([4,1])
with f_col1:
    st.caption(f"Ultimo aggiornamento: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}")
with f_col2:
    if st.button("🔄 AGGIORNA DATI"):
        st.cache_data.clear()
        st.rerun()