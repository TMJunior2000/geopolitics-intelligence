import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import GLOBAL_STYLES, CARD_CSS
from frontend.ui.cards import generate_grid_html

st.set_page_config(page_title="Trading Intel 3.0", layout="wide", page_icon="🧠")
st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache 5 minuti
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
<div class="hero-header">
    <div class="hero-title">Trading Intelligence</div>
    <div class="hero-subtitle">🚀 AI-POWERED MARKET ANALYSIS</div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Nessun dato trovato nel database.")
    st.stop()

# --- FILTRI (8 per riga, multiple righe) ---
unique_assets = sorted(df['asset_ticker'].unique().tolist())
all_assets = ["TUTTI"] + unique_assets

if 'active_filter' not in st.session_state:
    st.session_state.active_filter = "TUTTI"

st.markdown("<div class='nav-title'>🎯 Filter by Asset</div>", unsafe_allow_html=True)

# Creiamo righe di massimo 8 bottoni
buttons_per_row = 8
for row_start in range(0, len(all_assets), buttons_per_row):
    row_assets = all_assets[row_start:row_start + buttons_per_row]
    cols = st.columns(len(row_assets))
    
    for i, asset in enumerate(row_assets):
        with cols[i]:
            display_text = "🌐 TUTTI" if asset == "TUTTI" else asset
            is_active = st.session_state.active_filter == asset
            
            if st.button(display_text, key=f"btn_{asset}", 
                        type="primary" if is_active else "secondary",
                        use_container_width=True):
                st.session_state.active_filter = asset
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- RENDER CARDS CON HTML COMPONENT ---
target_list = unique_assets if st.session_state.active_filter == "TUTTI" else [st.session_state.active_filter]
html_cards = generate_grid_html(df, target_list)

# Calcolo altezza: ogni card ~520px + spacing
num_cards = len(df[df['asset_ticker'].isin(target_list)])
cards_per_row = 3
rows = (num_cards + cards_per_row - 1) // cards_per_row  # Arrotonda per eccesso
component_height = max(600, rows * 560 + 200)  # Aggiungi padding extra

components.html(
    f"""
    <html>
    <head>
        <meta charset="utf-8">
        {CARD_CSS}
    </head>
    <body>
        {html_cards}
    </body>
    </html>
    """,
    height=component_height,
    scrolling=True  # IMPORTANTE: True per vedere tutte le card
)

# --- FOOTER ---
st.markdown("---")
f_col1, f_col2, f_col3 = st.columns([2, 2, 1])
with f_col1:
    st.caption(f"📊 {num_cards} insights disponibili")
with f_col2:
    st.caption(f"🕐 Ultimo aggiornamento: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")
with f_col3:
    if st.button("🔄 REFRESH", use_container_width=True):
        st.cache_data.clear()
        st.rerun()