import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import GLOBAL_STYLES, CARD_CSS
from frontend.ui.cards import generate_grid_html

# Setup
st.set_page_config(page_title="Trading Intel", layout="wide", page_icon="🍊")
st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

# Data Loading
@st.cache_data(ttl=300)
def load_data():
    repo = MarketRepository()
    raw = repo.get_all_insights_flat()
    if not raw: return pd.DataFrame()
    df = pd.DataFrame(raw)
    if 'published_at' in df.columns:
        df['published_at'] = pd.to_datetime(df['published_at'])
    return df

df = load_data()

# Header
st.markdown("<h1 style='text-align:center;'>Trading Intelligence</h1>", unsafe_allow_html=True)

if df.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# Filters
all_assets = ["SHOW ALL"] + sorted(df['asset_ticker'].unique().tolist())
if 'filter' not in st.session_state: st.session_state.filter = "SHOW ALL"

cols = st.columns(8)
for i, asset in enumerate(all_assets):
    with cols[i % 8]:
        kind = "primary" if st.session_state.filter == asset else "secondary"
        if st.button(asset, key=asset, type=kind, use_container_width=True):
            st.session_state.filter = asset
            st.rerun()

# Rendering
target_assets = all_assets[1:] if st.session_state.filter == "SHOW ALL" else [st.session_state.filter]
html_content = generate_grid_html(df, target_assets)

components.html(
    f"<html><head>{CARD_CSS}</head><body>{html_content}</body></html>",
    height=800, scrolling=True
)

if st.button("🔄 REFRESH"):
    st.cache_data.clear()
    st.rerun()