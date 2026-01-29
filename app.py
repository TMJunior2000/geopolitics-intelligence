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

# ==============================================================================
# 1. CSS PER L'INTERFACCIA STREAMLIT (FILTRI E BOTTONI)
# Questo CSS agisce sugli elementi nativi di Streamlit (fuori dall'iframe delle card)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* BASE BACKGROUND APP */
    .stApp {
        background: #0E1117; 
    }

    /* HEADER */
    h1, h2, h3, p, div {
        font-family: 'Inter', sans-serif;
        color: #FAFAFA;
    }

    /* --- FIX BOTTONI FILTRO (DIMENSIONI IDENTICHE) --- */
    div[data-testid="column"] button {
        width: 100% !important;        /* Occupa tutta la larghezza della colonna */
        height: 50px !important;       /* Altezza fissa */
        min-height: 50px !important;
        max-height: 50px !important;
        border-radius: 12px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        border: none !important;
        transition: transform 0.2s !important;
        white-space: nowrap !important; /* Evita che il testo vada a capo */
        overflow: hidden !important;    /* Taglia testo troppo lungo */
        text-overflow: ellipsis !important; /* Mette i puntini ... */
    }

    /* Stile Bottone Selezionato (Primary) */
    div[data-testid="column"] button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
        border: none !important;
    }

    /* Stile Bottone Non Selezionato (Secondary) */
    div[data-testid="column"] button[kind="secondary"] {
        background: #1E232F !important; 
        color: #A0AEC0 !important;
        border: 1px solid #2D3748 !important;
    }
    div[data-testid="column"] button[kind="secondary"]:hover {
        border-color: #667eea !important;
        color: #667eea !important;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. CSS PER LE CARD (INTERNO ALL'IFRAME)
# Ho ridotto l'altezza a 360px per rimuovere il "buco bianco"
# ==============================================================================
CARD_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* BASE IFRAME */
    html, body {
        font-family: 'Inter', sans-serif;
        background: #0E1117; /* Deve combaciare con lo sfondo app */
        color: #FAFAFA;
        margin: 0;
        padding: 0;
        overflow-x: hidden; /* Evita scroll orizzontale */
    }

    /* CARD CONTAINER - ALTEZZA RIDOTTA */
    .modern-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        
        /* ALTEZZA RIDOTTA: Da 520px a 360px per togliere lo spazio vuoto */
        height: 360px !important; 
        
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        position: relative;
        overflow: hidden;
        border: 2px solid transparent; 
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        box-sizing: border-box; /* Importante per padding */
    }

    .modern-card:hover {
        transform: translateY(-8px);
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
        height: 30px !important;
        display: flex;
        align-items: center;
        margin-bottom: 10px;
    }
    .pill-tag {
        padding: 4px 12px;
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
        font-size: 18px;
        line-height: 1.3;
        color: #1A1A2E;
        font-weight: 700;
        margin-bottom: 10px;
        height: 48px !important; /* Spazio per 2 righe */
        min-height: 48px !important;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    /* TESTO */
    .card-text {
        font-size: 14px;
        color: #4A5568;
        line-height: 1.5;
        height: 85px !important; /* Ridotto per card più compatta */
        min-height: 85px !important;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        margin-bottom: 15px;
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
        margin-bottom: 10px;
        height: 20px;
    }
    
    .source-badge {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 140px;
    }

    /* CTA BUTTON STYLE */
    a.cta-button {
        display: flex !important;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 42px !important;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        text-transform: uppercase;
        font-size: 12px;
        text-decoration: none !important;
        transition: transform 0.2s;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11);
        border: none;
        cursor: pointer;
    }
    a.cta-button:hover {
        transform: scale(1.02);
        color: white !important;
    }

    /* GRID LAYOUT */
    .cards-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        padding-bottom: 20px;
    }

    /* ASSET HEADER */
    .asset-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 28px;
        font-weight: 700;
        color: #FAFAFA;
        margin-top: 30px;
        margin-bottom: 20px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 10px;
    }
</style>
"""

# --- LOGICA DATI ---
db = DBService()

@st.cache_data(ttl=300)
def load_data():
    try:
        raw_data = db.get_all_insights_dataframe()
        if not raw_data: return pd.DataFrame()
        df = pd.DataFrame(raw_data)
        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'])
            df = df.sort_values(by='published_at', ascending=False)
        return df
    except: return pd.DataFrame()

df = load_data()

# --- FUNZIONE GENERAZIONE HTML ---
def generate_card_html(row):
    sid = row.get('source_id', 0)
    source_class = f"source-{sid}" if sid in [1, 2] else "source-default"
    
    sent = str(row.get('sentiment', 'NEUTRAL')).upper()
    tag_class = "tag-bullish" if sent == "BULLISH" else "tag-bearish" if sent == "BEARISH" else "tag-neutral"
    sent_icon = "🚀" if sent == "BULLISH" else "📉" if sent == "BEARISH" else "⚖️"
    
    title = html.escape(str(row.get('video_title', 'No Title')))
    reasoning = html.escape(str(row.get('ai_reasoning', 'No reasoning available.')))
    source_name = html.escape(str(row.get('video_title', '')).split(':')[0][:20])
    date_str = row['published_at'].strftime('%d %b %Y') if 'published_at' in row and pd.notna(row['published_at']) else "N/A"
    
    url = row.get('video_url', '#')
    if not url or url == 'nan': url = "#"
    
    # HTML SENZA SPAZI EXTRA
    return f"""
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

def generate_all_cards_html(df, assets_to_show):
    all_html_parts = []
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty: continue
        
        all_html_parts.append(f'<div class="asset-header">💎 {html.escape(asset)}</div>')
        all_html_parts.append('<div class="cards-grid">')
        for _, row in asset_df.iterrows():
            all_html_parts.append(generate_card_html(row))
        all_html_parts.append('</div>')
    return ''.join(all_html_parts)

# --- HEADER APP ---
st.markdown("""
<div style="text-align:center; padding: 30px 0;">
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

# Gestione righe bottoni
cols = st.columns(8)
for i, asset in enumerate(all_assets):
    col_idx = i % 8
    if i > 0 and i % 8 == 0:
        cols = st.columns(8)
    with cols[col_idx]:
        btn_type = "primary" if st.session_state.selected_filter == asset else "secondary"
        label = "🌐 ALL" if asset == "SHOW ALL" else asset
        # Nota: il CSS esterno ora forza questi bottoni ad avere la stessa dimensione
        if st.button(label, key=f"btn_{asset}", type=btn_type, use_container_width=True):
            st.session_state.selected_filter = asset
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- RENDER IFRAME ---
assets_to_show = unique_assets if st.session_state.selected_filter == "SHOW ALL" else [st.session_state.selected_filter]
all_cards_html = generate_all_cards_html(df, assets_to_show)

# Calcolo altezza dinamica (aggiornato per card più corte)
total_cards = sum(len(df[df['asset_ticker'] == asset]) for asset in assets_to_show)
rows = (total_cards + 2) // 3 
# Altezza stimata: 360px card + 20px gap + header asset circa 60px
iframe_height = max(500, rows * 420) 

components.html(
    f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {CARD_CSS}
    </head>
    <body style="background: #0E1117; padding: 10px; margin: 0;">
        {all_cards_html}
    </body>
    </html>
    """,
    height=iframe_height,
    scrolling=False
)

# REFRESH
st.markdown("<br><br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 REFRESH DATA", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()