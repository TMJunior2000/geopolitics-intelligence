import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from database.repository import MarketRepository
from frontend.ui.styles import GLOBAL_STYLES, CARD_CSS
from frontend.ui.cards import generate_grid_html

st.set_page_config(page_title="Trading Intel 3.0", layout="wide", page_icon="🧠")
st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

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

# --- UI HEADER (ORIGINALE) ---
st.markdown("""
<div style="text-align:center; padding: 20px 0;">
    <h1 style="font-family:'Space Grotesk'; font-size: 50px; margin:0;">🧠 Trading Intelligence</h1>
    <p style="color:#888; letter-spacing:2px;">AI-POWERED MARKET ANALYSIS TERMINAL</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Nessun dato trovato nel database.")
    st.stop()

# --- FILTRI (8 PER RIGA) ---
unique_assets = sorted(df['asset_ticker'].unique().tolist())
all_assets = ["TUTTI"] + unique_assets

if 'active_filter' not in st.session_state:
    st.session_state.active_filter = "TUTTI"

# Dividiamo in righe da 8
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
html_cards = generate_grid_html(df, target_list)

# Calcolo altezza REALE per mostrare tutto senza scroll
num_cards = len(df[df['asset_ticker'].isin(target_list)])
cards_per_row = 3
rows = (num_cards + cards_per_row - 1) // cards_per_row

# Calcolo preciso:
# - Ogni card: 480px (altezza) + 25px (gap) = 505px per riga
# - Ogni asset header: 90px
# - Padding body: 20px top + 20px bottom = 40px
component_height = (rows * 505) + (len(target_list) * 90) + 40 + 100  # +100 margine sicurezza

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
    scrolling=False
)

# --- FOOTER ---
st.markdown("---")
f_col1, f_col2 = st.columns([4,1])
with f_col1:
    st.caption(f"📊 {num_cards} insights | Ultimo aggiornamento: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}")
with f_col2:
    if st.button("🔄 AGGIORNA DATI", use_container_width=True):
        st.cache_data.clear()
        st.rerun()