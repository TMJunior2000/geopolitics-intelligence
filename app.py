import streamlit as st
import pandas as pd
from services.db_service import DBService

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Trading Intelligence",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 1. CSS CUSTOM (GEN Z VIBES) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* BASE */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    /* MAIN CONTAINER */
    .main > div {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 30px;
        padding: 40px;
        margin: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }

    /* HEADER CUSTOM */
    .hero-header {
        text-align: center;
        margin-bottom: 50px;
        padding: 30px;
        background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 50%, #4ECDC4 100%);
        border-radius: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 56px;
        font-weight: 700;
        background: linear-gradient(45deg, #1A1A2E, #16213E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -2px;
    }
    
    .hero-subtitle {
        font-size: 18px;
        color: #2D3748;
        margin-top: 10px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 3px;
    }

    /* NAVIGATION TITLE */
    .nav-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 20px;
        font-weight: 700;
        color: #1A1A2E;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 20px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.05);
    }

    /* FIX BOTTONI STREAMLIT - LARGHEZZA E ALTEZZA RESPONSIVE */
    div[data-testid="column"] {
        display: flex !important;
        align-items: stretch !important;
    }
    
    div[data-testid="column"] > div {
        width: 100% !important;
    }
    
    div[data-testid="column"] button {
        width: 100% !important;
        min-width: 100px !important;
        height: 55px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        border-radius: 15px !important;
        border: 3px solid transparent !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        padding: 0 10px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    /* PRIMARY BUTTON (SELECTED) */
    div[data-testid="column"] button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: 3px solid #667eea !important;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4) !important;
        transform: scale(1.05);
    }
    
    /* SECONDARY BUTTON (NOT SELECTED) */
    div[data-testid="column"] button[kind="secondary"] {
        background: #F7FAFC !important;
        color: #4A5568 !important;
        border: 3px solid #E2E8F0 !important;
    }
    
    div[data-testid="column"] button[kind="secondary"]:hover {
        background: white !important;
        border-color: #CBD5E0 !important;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1) !important;
    }

    /* TITOLI SEZIONI ASSET */
    .asset-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 38px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 60px 0 30px 0;
        padding: 20px;
        border-radius: 15px;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        -webkit-background-clip: inherit;
        -webkit-text-fill-color: inherit;
        color: #1A1A2E;
        display: flex;
        align-items: center;
        gap: 15px;
    }

    /* CARD DESIGN (GLASSMORPHISM + GRADIENT BORDERS) - ALTEZZA FISSA */
    .modern-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-radius: 25px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border: 2px solid rgba(255, 255, 255, 0.3);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 420px;
        min-height: 420px;
        max-height: 420px;
        position: relative;
        overflow: hidden;
    }
    
    .modern-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 6px;
        background: linear-gradient(90deg, #FF6B6B, #FFE66D, #4ECDC4);
        border-radius: 25px 25px 0 0;
    }
    
    /* COLORI ACCENTO PER CANALE */
    .source-1::before { background: linear-gradient(90deg, #FF6B6B, #FF8E53) !important; }
    .source-2::before { background: linear-gradient(90deg, #E63946, #F77F00) !important; }
    .source-default::before { background: linear-gradient(90deg, #4ECDC4, #556270) !important; }

    .modern-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        border-color: rgba(102, 126, 234, 0.5);
    }

    /* TAGS (PIÙ BOLD E COLORATI) */
    .pill-tag {
        display: inline-block;
        padding: 8px 18px;
        border-radius: 50px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 15px;
        letter-spacing: 1px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    .tag-bullish { 
        background: linear-gradient(135deg, #06FFA5, #4ECDC4); 
        color: #0F4C3A;
    }
    .tag-bearish { 
        background: linear-gradient(135deg, #FF6B6B, #E63946); 
        color: white;
    }
    .tag-neutral { 
        background: linear-gradient(135deg, #A8DADC, #457B9D); 
        color: white;
    }

    /* CARD TITLE */
    .card-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 22px;
        line-height: 1.4;
        margin: 15px 0;
        color: #1A1A2E;
        font-weight: 700;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        text-overflow: ellipsis;
        min-height: 62px;
        max-height: 62px;
    }

    /* CARD TEXT */
    .card-text {
        color: #4A5568;
        font-size: 15px;
        line-height: 1.6;
        margin: 15px 0;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        text-overflow: ellipsis;
        flex: 1;
    }

    /* META INFO */
    .card-meta {
        font-size: 13px;
        color: #718096;
        font-weight: 600;
        margin-top: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 20px;
        border-top: 2px solid #F7FAFC;
    }
    
    .source-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
    }
    
    .date-badge {
        display: flex;
        align-items: center;
        gap: 5px;
        color: #718096;
    }

    /* CTA BUTTON */
    .cta-button {
        width: 100%;
        border-radius: 15px;
        border: none;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        cursor: pointer;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        margin-top: 20px;
    }
    
    .cta-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.5);
    }

    /* REFRESH BUTTON */
    .stButton > button[data-baseweb="button"] {
        background: linear-gradient(135deg, #06FFA5, #4ECDC4) !important;
        color: #0F4C3A !important;
        font-weight: 700 !important;
        border-radius: 20px !important;
        padding: 20px 40px !important;
        font-size: 16px !important;
        border: none !important;
        box-shadow: 0 10px 25px rgba(6, 255, 165, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button[data-baseweb="button"]:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 15px 35px rgba(6, 255, 165, 0.5) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGICA DATI CON CACHE ---
db = DBService()

@st.cache_data(ttl=300)  # Cache per 5 minuti (300 secondi)
def load_data():
    """
    Carica i dati dal database con caching.
    TTL = 5 minuti: i dati vengono ricaricati automaticamente ogni 5 minuti.
    """
    raw_data = db.get_all_insights_dataframe()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)
    df['published_at'] = pd.to_datetime(df['published_at'])
    df = df.sort_values(by='published_at', ascending=False)
    return df

# Carica dati (usa cache se disponibile)
df = load_data()

# --- 3. UI: HEADER ---
st.markdown("""
<div class='hero-header'>
    <div class='hero-title'>Trading Intelligence</div>
    <div class='hero-subtitle'>🚀 Market Analysis Dashboard</div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.info("⏳ Loading data from backend...")
    st.stop()

# --- 4. NAVIGAZIONE A BOTTONI (PILLS) - FIXED SCROLLABLE ---
st.markdown("<div class='nav-title'>🎯 Filter by Asset</div>", unsafe_allow_html=True)

unique_assets = sorted(df['asset_ticker'].unique().tolist())

if 'selected_filter' not in st.session_state:
    st.session_state.selected_filter = "SHOW ALL"

# Mostriamo solo 8 bottoni per riga (più gestibile visivamente)
buttons_per_row = 8
all_assets = ["SHOW ALL"] + unique_assets

# Creiamo righe di bottoni
for row_start in range(0, len(all_assets), buttons_per_row):
    row_assets = all_assets[row_start:row_start + buttons_per_row]
    cols = st.columns(len(row_assets))
    
    for i, asset in enumerate(row_assets):
        with cols[i]:
            display_text = "🌐 ALL" if asset == "SHOW ALL" else asset
            btn_type = "primary" if st.session_state.selected_filter == asset else "secondary"
            
            if st.button(display_text, use_container_width=True, key=f"btn_{asset}", type=btn_type):
                st.session_state.selected_filter = asset
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- 5. RENDER DELLE SEZIONI ---
assets_to_show = unique_assets if st.session_state.selected_filter == "SHOW ALL" else [st.session_state.selected_filter]

for asset in assets_to_show:
    # Emoji per asset (personalizzabili)
    asset_emoji = {
        'BTC': '₿', 'ETH': '⟠', 'SPX': '📈', 
        'GOLD': '🥇', 'OIL': '🛢️'
    }.get(asset, '💎')
    
    st.markdown(f"<div class='asset-header'>{asset_emoji} {asset}</div>", unsafe_allow_html=True)
    
    asset_df = df[df['asset_ticker'] == asset]
    
    grid = st.columns(3)
    
    for i, (_, row) in enumerate(asset_df.iterrows()):
        with grid[i % 3]:
            sid = row.get('source_id', 0)
            source_class = f"source-{sid}" if sid in [1, 2] else "source-default"
            
            sent = str(row.get('sentiment', 'NEUTRAL'))
            tag_class = "tag-bullish" if sent == "BULLISH" else "tag-bearish" if sent == "BEARISH" else "tag-neutral"
            sentiment_emoji = "🚀" if sent == "BULLISH" else "📉" if sent == "BEARISH" else "⚖️"
            
            # Escape HTML per evitare rendering di codice
            import html
            title = html.escape(row.get('video_title', 'No Title'))
            reasoning = html.escape(row.get('ai_reasoning', '')[:200])
            source_name = html.escape(row.get('video_title', '').split(':')[0][:15])
            
            video_url = row.get('video_url', '#')
            date_str = row['published_at'].strftime('%d %b %Y')
            
            st.markdown(f"""
            <div class="modern-card {source_class}">
                <div>
                    <span class="pill-tag {tag_class}">{sentiment_emoji} {sent}</span>
                    <div class="card-title">{title}</div>
                    <div class="card-text">{reasoning}...</div>
                </div>
                <div class="card-meta">
                    <span class="source-badge">📺 {source_name}</span>
                    <span class="date-badge">📅 {date_str}</span>
                </div>
                <a href="{video_url}" target="_blank" style="text-decoration: none;">
                    <button class="cta-button">
                        👁️ View Full Analysis
                    </button>
                </a>
            </div>
            """, unsafe_allow_html=True)

# --- BOTTONE REFRESH ---
st.markdown("<br><br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 REFRESH DATA", use_container_width=True):
        # Pulisce la cache e ricarica
        st.cache_data.clear()
        st.rerun()