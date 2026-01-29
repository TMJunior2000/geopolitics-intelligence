import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import html
from services.db_service import DBService

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Trading Intelligence",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 1. CSS BLINDATO ---
GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* BASE */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background: #0E1117; 
        color: #FAFAFA;
    }

    /* CARD CONTAINER */
    .modern-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        height: 520px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        position: relative;
        overflow: hidden;
        border: 2px solid transparent; 
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }

    .modern-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        border-color: #667eea;
        z-index: 10;
    }

    /* DECORAZIONE SUPERIORE */
    .modern-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 6px;
        background: linear-gradient(90deg, #FF6B6B, #FFE66D);
    }
    .source-1::before { background: linear-gradient(90deg, #FF6B6B, #FF8E53) !important; }
    .source-2::before { background: linear-gradient(90deg, #06FFA5, #4ECDC4) !important; }

    /* TAG SECTION */
    .tag-container {
        height: 40px !important;
        display: flex;
        align-items: center;
    }
    .pill-tag {
        padding: 5px 12px;
        border-radius: 50px;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        color: white;
        letter-spacing: 0.5px;
    }
    .tag-bullish { background: #06FFA5; color: #004d40; }
    .tag-bearish { background: #FF6B6B; color: white; }
    .tag-neutral { background: #A8DADC; color: #1A1A2E; }

    /* TITOLO */
    .card-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 20px;
        line-height: 1.3;
        color: #1A1A2E;
        font-weight: 700;
        margin-bottom: 15px;
        height: 54px !important; 
        min-height: 54px !important;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    /* TESTO */
    .card-text {
        font-size: 14px;
        color: #4A5568;
        line-height: 1.6;
        height: 115px !important; 
        min-height: 115px !important;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 5;
        -webkit-box-orient: vertical;
        margin-bottom: 20px;
    }

    /* FOOTER */
    .card-footer {
        margin-top: auto;
        width: 100%;
        border-top: 1px solid #F0F0F0;
        padding-top: 15px;
    }

    .card-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        color: #718096;
        font-weight: 600;
        margin-bottom: 15px;
        height: 20px;
    }
    
    .source-badge {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 150px;
    }

    /* CTA BUTTON STYLE */
    a.cta-button {
        display: flex !important;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 48px !important;
        border-radius: 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        text-transform: uppercase;
        font-size: 13px;
        text-decoration: none !important;
        transition: transform 0.2s;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        border: none;
        cursor: pointer;
    }
    a.cta-button:hover {
        transform: scale(1.02);
        box-shadow: 0 7px 14px rgba(50, 50, 93, 0.1), 0 3px 6px rgba(0, 0, 0, 0.08);
        color: white !important;
    }

    /* GRID LAYOUT */
    .cards-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 24px;
        margin-bottom: 40px;
    }

    /* ASSET HEADER */
    .asset-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 32px;
        font-weight: 700;
        color: #FAFAFA;
        margin-top: 40px;
        margin-bottom: 24px;
    }
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# --- 2. LOGICA DATI ---
db = DBService()

@st.cache_data(ttl=300)
def load_data():
    try:
        raw_data = db.get_all_insights_dataframe()
        if not raw_data: 
            return pd.DataFrame()
        df = pd.DataFrame(raw_data)
        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'])
            df = df.sort_values(by='published_at', ascending=False)
        return df
    except: 
        return pd.DataFrame()

df = load_data()

# --- 3. FUNZIONE PER GENERARE CARD HTML ---
def generate_card_html(row):
    """
    Genera l'HTML completo di una singola card
    """
    # Preparazione Dati
    sid = row.get('source_id', 0)
    source_class = f"source-{sid}" if sid in [1, 2] else "source-default"
    
    sent = str(row.get('sentiment', 'NEUTRAL')).upper()
    tag_class = "tag-bullish" if sent == "BULLISH" else "tag-bearish" if sent == "BEARISH" else "tag-neutral"
    sent_icon = "🚀" if sent == "BULLISH" else "📉" if sent == "BEARISH" else "⚖️"
    
    # Escape HTML per sicurezza
    title = html.escape(str(row.get('video_title', 'No Title')))
    reasoning = html.escape(str(row.get('ai_reasoning', 'No reasoning available.')))
    source_name = html.escape(str(row.get('video_title', '')).split(':')[0][:20])
    date_str = row['published_at'].strftime('%d %b %Y') if 'published_at' in row and pd.notna(row['published_at']) else "N/A"
    
    url = row.get('video_url', '#')
    if not url or url == 'nan':
        url = "#"
    
    # HTML della card
    card_html = f"""
    <div class="modern-card {source_class}">
        <div class="tag-container">
            <span class="pill-tag {tag_class}">{sent_icon} {sent}</span>
        </div>
        <div class="card-title" title="{title}">{title}</div>
        <div class="card-text">{reasoning}</div>
        <div class="card-footer">
            <div class="card-meta">
                <span class="source-badge" title="{source_name}">📺 {source_name}</span>
                <span>📅 {date_str}</span>
            </div>
            <a href="{url}" target="_blank" class="cta-button">
                👁️ VIEW FULL ANALYSIS
            </a>
        </div>
    </div>
    """
    return card_html


def generate_all_cards_html(df, assets_to_show):
    """
    Genera l'HTML completo per tutti gli asset e le loro card
    Questo approccio senior permette un rendering più efficiente e controllato
    """
    all_html_parts = []
    
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty:
            continue
        
        # Header dell'asset
        all_html_parts.append(f'<div class="asset-header">💎 {html.escape(asset)}</div>')
        
        # Apertura grid
        all_html_parts.append('<div class="cards-grid">')
        
        # Genera tutte le card per questo asset
        for _, row in asset_df.iterrows():
            card_html = generate_card_html(row)
            all_html_parts.append(card_html)
        
        # Chiusura grid
        all_html_parts.append('</div>')
    
    return ''.join(all_html_parts)


# --- HEADER ---
st.markdown("""
<div style="text-align:center; padding: 40px 0;">
    <h1 style="font-family:'Space Grotesk'; font-size:48px; margin:0; color:#FAFAFA;">Trading Intelligence</h1>
    <p style="color:#888; text-transform:uppercase; letter-spacing:2px; font-weight:600;">🚀 Market Analysis Dashboard</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Nessun dato trovato.")
    st.stop()

# --- FILTRI ---
st.markdown("### 🎯 Filter by Asset")
unique_assets = sorted(df['asset_ticker'].unique().tolist())
all_assets = ["SHOW ALL"] + unique_assets

if 'selected_filter' not in st.session_state:
    st.session_state.selected_filter = "SHOW ALL"

cols = st.columns(8)
for i, asset in enumerate(all_assets):
    col_idx = i % 8
    if i > 0 and i % 8 == 0:
        cols = st.columns(8)
    with cols[col_idx]:
        btn_type = "primary" if st.session_state.selected_filter == asset else "secondary"
        label = "🌐 ALL" if asset == "SHOW ALL" else asset
        if st.button(label, key=f"btn_{asset}", type=btn_type, use_container_width=True):
            st.session_state.selected_filter = asset
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- RENDER CARDS (APPROCCIO SENIOR) ---
assets_to_show = unique_assets if st.session_state.selected_filter == "SHOW ALL" else [st.session_state.selected_filter]

# Genera tutto l'HTML in una volta
all_cards_html = generate_all_cards_html(df, assets_to_show)

# Calcola altezza dinamica basata sul numero di card
total_cards = sum(len(df[df['asset_ticker'] == asset]) for asset in assets_to_show)
rows = (total_cards + 2) // 3  # Arrotonda per eccesso
height = max(600, rows * 580)  # 580px per riga (card + margini)

# Rendering con st.components - QUESTO È IL METODO SENIOR
components.html(
    f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {GLOBAL_CSS}
    </head>
    <body style="background: #0E1117; padding: 20px; margin: 0;">
        {all_cards_html}
    </body>
    </html>
    """,
    height=height,
    scrolling=False
)

# REFRESH BUTTON
st.markdown("<br><br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 REFRESH DATA", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()