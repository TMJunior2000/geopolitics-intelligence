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

# --- 1. CSS CUSTOM (CORRETTO E PULITO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* BASE */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    .main > div {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 30px;
        padding: 40px;
        margin: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }

    /* HEADER */
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

    /* --- FIX BOTTONI FILTRO --- */
    /* Targettiamo i bottoni dentro le colonne per farli uguali */
    div[data-testid="stHorizontalBlock"] button {
        width: 100% !important;  /* Occupa tutta la larghezza della colonna */
        height: 55px !important; /* Altezza fissa per tutti */
        border-radius: 12px !important;
        font-weight: 700 !important;
        border: 2px solid transparent !important;
        font-family: 'Space Grotesk', sans-serif !important;
        transition: all 0.2s ease !important;
    }

    /* Stile Bottoni Primary (Attivi) */
    button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    }

    /* Stile Bottoni Secondary (Inattivi) */
    button[kind="secondary"] {
        background: #F7FAFC !important;
        color: #4A5568 !important;
        border: 2px solid #E2E8F0 !important;
    }
    button[kind="secondary"]:hover {
        border-color: #667eea !important;
        color: #667eea !important;
        background: white !important;
    }

    /* ASSET HEADER */
    .asset-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 32px;
        font-weight: 700;
        margin: 40px 0 20px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid rgba(0,0,0,0.05);
        color: #1A1A2E;
    }

    /* --- FIX CARD DIMENSIONI FISSE --- */
    .modern-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px solid rgba(255,255,255,0.6);
        
        /* MAGIC SAUCE PER ALTEZZA FISSA */
        height: 450px !important;       /* Altezza forzata */
        display: flex !important;       /* Flexbox */
        flex-direction: column !important; 
        justify-content: space-between !important; /* Spinge il footer giù */
        position: relative;
        overflow: hidden;
        transition: transform 0.3s ease;
    }

    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.1);
    }

    /* Decorazione superiore colorata */
    .modern-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 5px;
        background: linear-gradient(90deg, #FF6B6B, #FFE66D, #4ECDC4);
    }
    .source-1::before { background: linear-gradient(90deg, #FF6B6B, #FF8E53) !important; }
    .source-2::before { background: linear-gradient(90deg, #E63946, #F77F00) !important; }

    /* Contenuto interno card */
    .card-content {
        flex: 1; /* Occupa tutto lo spazio disponibile */
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .card-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 20px;
        font-weight: 700;
        color: #1A1A2E;
        margin: 15px 0 10px 0;
        line-height: 1.3;
        
        /* Tronca testo dopo 2 righe */
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 52px; /* Riserva spazio per 2 righe */
    }

    .card-text {
        font-size: 14px;
        color: #4A5568;
        line-height: 1.5;
        
        /* Tronca testo dopo 6 righe */
        display: -webkit-box;
        -webkit-line-clamp: 6;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    /* Footer della Card */
    .card-footer {
        margin-top: auto; /* Si ancora al fondo */
        padding-top: 15px;
        border-top: 1px solid #F0F0F0;
    }

    .card-meta {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: #718096;
        margin-bottom: 15px;
        font-weight: 600;
    }

    .cta-button {
        width: 100%;
        padding: 12px;
        border-radius: 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-align: center;
        text-decoration: none;
        font-weight: 700;
        font-size: 14px;
        display: block;
        transition: opacity 0.2s;
        border: none;
    }
    .cta-button:hover {
        opacity: 0.9;
        color: white;
    }
    
    /* TAGS */
    .pill-tag {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        display: inline-block;
    }
    .tag-bullish { background: #E6FFFA; color: #2C7A7B; border: 1px solid #B2F5EA; }
    .tag-bearish { background: #FFF5F5; color: #C53030; border: 1px solid #FED7D7; }
    .tag-neutral { background: #F7FAFC; color: #4A5568; border: 1px solid #E2E8F0; }

</style>
""", unsafe_allow_html=True)

# --- 2. LOGICA DATI ---
db = DBService()

def load_data():
    raw_data = db.get_all_insights_dataframe()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)
    # Assicurati che published_at esista
    if 'published_at' in df.columns:
        df['published_at'] = pd.to_datetime(df['published_at'])
        df = df.sort_values(by='published_at', ascending=False)
    return df

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

# --- 4. NAVIGAZIONE FILTRI ---
unique_assets = sorted(df['asset_ticker'].unique().tolist())
if 'selected_filter' not in st.session_state:
    st.session_state.selected_filter = "SHOW ALL"

# Titolo sezione filtri
st.markdown("### 🎯 Filter by Asset")

# Layout Bottoni: Usiamo st.columns per garantire larghezza uguale
# Aggiungiamo il tasto "ALL" alla lista
all_filters = ["SHOW ALL"] + unique_assets
cols = st.columns(len(all_filters))

for i, filter_name in enumerate(all_filters):
    with cols[i]:
        # Etichetta bottone
        label = "🌐 ALL" if filter_name == "SHOW ALL" else filter_name
        # Tipo bottone (Primary se selezionato)
        btn_type = "primary" if st.session_state.selected_filter == filter_name else "secondary"
        
        if st.button(label, key=f"btn_{filter_name}", type=btn_type, use_container_width=True):
            st.session_state.selected_filter = filter_name
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- 5. RENDER DELLE CARD ---
assets_to_show = unique_assets if st.session_state.selected_filter == "SHOW ALL" else [st.session_state.selected_filter]

for asset in assets_to_show:
    # Emoji
    asset_emoji = {'BTC': '₿', 'ETH': '⟠', 'SPX': '📈', 'GOLD': '🥇', 'OIL': '🛢️'}.get(asset, '💎')
    
    st.markdown(f"<div class='asset-header'>{asset_emoji} {asset}</div>", unsafe_allow_html=True)
    
    asset_df = df[df['asset_ticker'] == asset]
    
    # Griglia 3 colonne
    grid = st.columns(3)
    
    for i, (_, row) in enumerate(asset_df.iterrows()):
        with grid[i % 3]:
            # Preparazione dati per HTML
            sid = row.get('source_id', 0)
            source_class = f"source-{sid}" if sid in [1, 2] else "source-default"
            
            sent = str(row.get('sentiment', 'NEUTRAL'))
            tag_class = "tag-bullish" if sent == "BULLISH" else "tag-bearish" if sent == "BEARISH" else "tag-neutral"
            sentiment_emoji = "🚀" if sent == "BULLISH" else "📉" if sent == "BEARISH" else "⚖️"
            
            title = row.get('video_title', 'No Title')
            reasoning = row.get('ai_reasoning', '')
            
            # Formattazione Data
            date_str = row['published_at'].strftime('%d %b') if 'published_at' in row else "N/A"
            source_name = row.get('video_title', '').split(':')[0][:12] # Accorcia nome fonte

            # --- CARD HTML ---
            # Nota l'uso di Flexbox interno: card-content spinge card-footer in basso
            st.markdown(f"""
            <div class="modern-card {source_class}">
                <div class="card-content">
                    <div>
                        <span class="pill-tag {tag_class}">{sentiment_emoji} {sent}</span>
                    </div>
                    <div class="card-title">{title}</div>
                    <div class="card-text">{reasoning}</div>
                </div>
                
                <div class="card-footer">
                    <div class="card-meta">
                        <span>📺 {source_name}</span>
                        <span>📅 {date_str}</span>
                    </div>
                    <a href="{row.get('video_url', '#')}" target="_blank">
                        <button class="cta-button">
                            👁️ VIEW ANALYSIS
                        </button>
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- REFRESH ---
st.markdown("<br><br>", unsafe_allow_html=True)
_, col2, _ = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 REFRESH DATA", use_container_width=True):
        st.rerun()