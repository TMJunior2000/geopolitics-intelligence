import streamlit as st
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

# --- 1. CSS BLINDATO (LAYOUT RIGIDO E PERFETTO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* BASE */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background: #0E1117; /* Sfondo scuro (o gradiente se preferisci) */
        color: #FAFAFA;
    }

    /* MAIN CONTAINER */
    .main > div {
        padding: 20px;
    }

    /* HERO HEADER */
    .hero-header {
        text-align: center;
        margin-bottom: 40px;
        padding: 30px;
        background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 50%, #4ECDC4 100%);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 48px;
        font-weight: 700;
        color: #1A1A2E;
        margin: 0;
        letter-spacing: -1px;
    }

    .hero-subtitle {
        font-size: 16px;
        color: #2D3748;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 5px;
    }

    /* --- FILTRI E BOTTONI --- */
    /* Forza i bottoni Streamlit ad avere tutti la stessa dimensione */
    div[data-testid="column"] button {
        width: 100% !important;
        height: 50px !important;
        min-height: 50px !important;
        max-height: 50px !important;
        border-radius: 12px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        border: none !important;
        transition: transform 0.2s !important;
    }

    /* Bottone Selezionato (Primary) */
    button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    }

    /* Bottone Non Selezionato (Secondary) */
    button[kind="secondary"] {
        background: #1E232F !important; /* Scuro per contrasto */
        color: #A0AEC0 !important;
        border: 1px solid #2D3748 !important;
    }
    button[kind="secondary"]:hover {
        border-color: #667eea !important;
        color: #667eea !important;
    }

    /* --- CARD "BLINDATA" --- */
    .modern-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        
        /* ALTEZZA TOTALE FISSA */
        height: 500px !important;
        min-height: 500px !important;
        max-height: 500px !important;
        
        /* LAYOUT FLEX VERTICALE */
        display: flex !important;
        flex-direction: column !important;
        position: relative;
        overflow: hidden;
    }

    /* Decorazione superiore */
    .modern-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 6px;
        background: linear-gradient(90deg, #FF6B6B, #FFE66D);
    }
    .source-1::before { background: linear-gradient(90deg, #FF6B6B, #FF8E53) !important; }
    .source-2::before { background: linear-gradient(90deg, #06FFA5, #4ECDC4) !important; }

    /* CONTENUTO INTERNO */
    .card-content {
        flex: 1; /* Occupa lo spazio disponibile */
        display: flex;
        flex-direction: column;
    }

    /* TAG SENTIMENT */
    .pill-tag {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 50px;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 15px;
        color: white;
        width: fit-content;
    }
    .tag-bullish { background: #06FFA5; color: #004d40; }
    .tag-bearish { background: #FF6B6B; color: white; }
    .tag-neutral { background: #A8DADC; color: #1A1A2E; }

    /* TITOLO - ALTEZZA FISSA */
    .card-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 20px;
        line-height: 1.25;
        color: #1A1A2E;
        font-weight: 700;
        margin-bottom: 10px;
        
        /* FORZA ALTEZZA: 2 righe circa */
        height: 55px !important;
        min-height: 55px !important;
        max-height: 55px !important;
        
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    /* TESTO - ALTEZZA FISSA */
    .card-text {
        font-size: 14px;
        color: #4A5568;
        line-height: 1.6;
        
        /* FORZA ALTEZZA: 6 righe circa */
        height: 140px !important;
        min-height: 140px !important;
        max-height: 140px !important;
        
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 6;
        -webkit-box-orient: vertical;
        margin-bottom: 10px;
    }

    /* FOOTER - ALTEZZA FISSA */
    /* Margin top auto spinge il footer in basso, ma essendo le altezze sopra fisse, è ridondante ma sicuro */
    .card-footer {
        margin-top: auto; 
        width: 100%;
        border-top: 1px solid #EDF2F7;
        padding-top: 15px;
    }

    .card-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        color: #A0AEC0;
        font-weight: 600;
        margin-bottom: 15px;
        height: 25px; /* Altezza fissa */
    }

    .source-badge {
        background: #E2E8F0;
        color: #4A5568;
        padding: 4px 10px;
        border-radius: 6px;
        max-width: 130px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* BOTTONE CTA */
    .cta-button {
        width: 100%;
        height: 45px !important;
        border-radius: 10px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        border: none;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        text-transform: uppercase;
        font-size: 13px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none; /* Importante per i link */
        transition: transform 0.2s;
    }
    
    .cta-button:hover {
        transform: scale(1.02);
        color: white; /* Fix hover link color */
    }

    /* ASSET HEADER */
    .asset-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 32px;
        font-weight: 700;
        margin: 50px 0 25px 0;
        color: #FAFAFA;
        display: flex;
        align-items: center;
        gap: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGICA DATI ---
db = DBService()

@st.cache_data(ttl=300)
def load_data():
    try:
        raw_data = db.get_all_insights_dataframe()
        if not raw_data:
            return pd.DataFrame()
        df = pd.DataFrame(raw_data)
        
        # Gestione colonne mancanti
        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'])
            df = df.sort_values(by='published_at', ascending=False)
        return df
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. UI: HEADER ---
st.markdown("""
<div class='hero-header'>
    <div class='hero-title'>Trading Intelligence</div>
    <div class='hero-subtitle'>🚀 Market Analysis Dashboard</div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Nessun dato disponibile nel database.")
    st.stop()

# --- 4. NAVIGAZIONE FILTRI (TABELLE ALLINEATE) ---
st.markdown("### 🎯 Filter by Asset")

unique_assets = sorted(df['asset_ticker'].unique().tolist())
all_assets = ["SHOW ALL"] + unique_assets

if 'selected_filter' not in st.session_state:
    st.session_state.selected_filter = "SHOW ALL"

# Definisci quante colonne per riga
cols_per_row = 6 

# Logica per creare righe di bottoni perfettamente allineati
for i in range(0, len(all_assets), cols_per_row):
    # Prendi un blocco di asset (es. i primi 6)
    batch = all_assets[i:i + cols_per_row]
    # Crea le colonne (se il batch è minore di cols_per_row, crea comunque colonne vuote per mantenere la griglia)
    cols = st.columns(cols_per_row)
    
    for j, asset_name in enumerate(batch):
        with cols[j]:
            label = "🌐 ALL" if asset_name == "SHOW ALL" else asset_name
            btn_type = "primary" if st.session_state.selected_filter == asset_name else "secondary"
            
            if st.button(label, key=f"btn_{asset_name}", type=btn_type, use_container_width=True):
                st.session_state.selected_filter = asset_name
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- 5. RENDER DELLE CARD ---
assets_to_show = unique_assets if st.session_state.selected_filter == "SHOW ALL" else [st.session_state.selected_filter]

for asset in assets_to_show:
    asset_df = df[df['asset_ticker'] == asset]
    if asset_df.empty:
        continue

    # Header Asset
    emoji_map = {'BTC': '₿', 'ETH': '⟠', 'SPX': '📈', 'GOLD': '🥇', 'OIL': '🛢️'}
    st.markdown(f"<div class='asset-header'>{emoji_map.get(asset, '💎')} {asset}</div>", unsafe_allow_html=True)
    
    # Grid Layout
    grid = st.columns(3)
    
    for i, (_, row) in enumerate(asset_df.iterrows()):
        with grid[i % 3]:
            # Dati
            sid = row.get('source_id', 0)
            source_class = f"source-{sid}" if sid in [1, 2] else "source-default"
            
            sent = str(row.get('sentiment', 'NEUTRAL'))
            tag_class = "tag-bullish" if sent == "BULLISH" else "tag-bearish" if sent == "BEARISH" else "tag-neutral"
            sent_icon = "🚀" if sent == "BULLISH" else "📉" if sent == "BEARISH" else "⚖️"
            
            # Escape HTML (Sicurezza + Visualizzazione corretta)
            title = html.escape(row.get('video_title', 'No Title'))
            reasoning = html.escape(row.get('ai_reasoning', ''))
            source_name = html.escape(row.get('video_title', '').split(':')[0])
            
            url = row.get('video_url', '#')
            date_str = row['published_at'].strftime('%d %b %Y') if 'published_at' in row else ""

            # HTML CARD
            st.markdown(f"""
            <div class="modern-card {source_class}">
                <div class="card-content">
                    <div>
                        <span class="pill-tag {tag_class}">{sent_icon} {sent}</span>
                    </div>
                    <div class="card-title">{title}</div>
                    <div class="card-text">{reasoning}</div>
                </div>
                
                <div class="card-footer">
                    <div class="card-meta">
                        <span class="source-badge" title="{source_name}">📺 {source_name}</span>
                        <span>📅 {date_str}</span>
                    </div>
                    <a href="{url}" target="_blank" style="text-decoration: none;">
                        <button class="cta-button">
                            👁️ VIEW FULL ANALYSIS
                        </button>
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- REFRESH ---
st.markdown("<br><br>", unsafe_allow_html=True)
_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    if st.button("🔄 REFRESH DATA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()