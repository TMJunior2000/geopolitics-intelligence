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

# --- 1. CSS CUSTOM (DESIGN SYSTEM AGGIORNATO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');

    /* BASE */
    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif;
        background-color: #F8F9FA;
    }

    /* TITOLI SEZIONI ASSET */
    .asset-header {
        font-size: 32px;
        font-weight: 700;
        color: #1E1E1E;
        margin: 40px 0 20px 0;
        padding-bottom: 10px;
        border-bottom: 3px solid #FF923B;
        display: inline-block;
    }

    /* CARD DESIGN (SENZA IMMAGINI) */
    .modern-card {
        background: white;
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        transition: all 0.3s ease;
        border: 1px solid #EEE;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 250px;
    }
    
    /* COLORI BORDI PER CANALE */
    /* Investire.biz (ID 1) -> Arancione */
    .source-1 { border-top: 10px solid #FF923B; }
    /* Investire biz - Analisi (ID 2) -> Dark Orange/Red */
    .source-2 { border-top: 10px solid #E65100; }
    /* MarketMind / Altri (Default) -> Blue */
    .source-default { border-top: 10px solid #2196F3; }

    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(0,0,0,0.08);
    }

    /* TAGS */
    .pill-tag {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .tag-bullish { background-color: #E8F5E9; color: #2E7D32; }
    .tag-bearish { background-color: #FFEBEE; color: #C62828; }
    .tag-neutral { background-color: #F5F5F5; color: #616161; }

    /* FONTE E DATA */
    .card-meta {
        font-size: 12px;
        color: #999;
        font-weight: 600;
        margin-top: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .source-name {
        color: #FF923B;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGICA DATI ---
db = DBService()

def load_data():
    raw_data = db.get_all_insights_dataframe()
    if not raw_data:
        return pd.DataFrame()
    df = pd.DataFrame(raw_data)
    # Ordine cronologico: più recenti in alto
    df['published_at'] = pd.to_datetime(df['published_at'])
    df = df.sort_values(by='published_at', ascending=False)
    return df

df = load_data()

# --- 3. UI: HEADER ---
st.markdown("<h1 style='font-size: 42px; margin-bottom:0;'>Trading<span style='color:#FF923B;'>Intelligence</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#888; font-size:18px;'>Market Analysis Dashboard</p>", unsafe_allow_html=True)

if df.empty:
    st.info("In attesa di dati dal backend...")
    st.stop()

# --- 4. NAVIGAZIONE A BOTTONI (PILLS) ---
st.write("### 🎯 Focus on:")
unique_assets = sorted(df['asset_ticker'].unique().tolist())
# Aggiungiamo un tasto "ALL"
cols = st.columns(len(unique_assets) + 1)

# Usiamo session_state per gestire quale asset è selezionato
if 'selected_filter' not in st.session_state:
    st.session_state.selected_filter = "SHOW ALL"

with cols[0]:
    if st.button("SHOW ALL", use_container_width=True, type="primary" if st.session_state.selected_filter == "SHOW ALL" else "secondary"):
        st.session_state.selected_filter = "SHOW ALL"
        st.rerun()

for i, asset in enumerate(unique_assets):
    with cols[i+1]:
        btn_type = "primary" if st.session_state.selected_filter == asset else "secondary"
        if st.button(asset, use_container_width=True, type=btn_type):
            st.session_state.selected_filter = asset
            st.rerun()

# --- 5. RENDER DELLE SEZIONI ---
# Decidiamo quali asset mostrare
assets_to_show = unique_assets if st.session_state.selected_filter == "SHOW ALL" else [st.session_state.selected_filter]

for asset in assets_to_show:
    st.markdown(f"<div class='asset-header'>{asset}</div>", unsafe_allow_html=True)
    
    # Filtriamo i dati per questo specifico asset
    asset_df = df[df['asset_ticker'] == asset]
    
    # Grid a 3 colonne per le card di questo asset
    grid = st.columns(3)
    
    for i, (_, row) in enumerate(asset_df.iterrows()):
        with grid[i % 3]:
            # Determinazione colore bordo basato su source_id
            sid = row.get('source_id', 0)
            source_class = f"source-{sid}" if sid in [1, 2] else "source-default"
            
            # Determinazione tag sentiment
            sent = str(row.get('sentiment', 'NEUTRAL'))
            tag_class = "tag-bullish" if sent == "BULLISH" else "tag-bearish" if sent == "BEARISH" else "tag-neutral"
            
            # Titolo pulito (evidenziazione keyword opzionale rimosso per pulizia estrema)
            title = row.get('video_title', 'No Title')
            
            # Render HTML Card
            st.markdown(f"""
            <div class="modern-card {source_class}">
                <div>
                    <span class="pill-tag {tag_class}">{sent}</span>
                    <h3 style="font-size: 20px; line-height: 1.3; margin-top: 10px;">{title}</h3>
                    <p style="color: #555; font-size: 14px; margin-top: 15px;">
                        {row.get('ai_reasoning', '')[:180]}...
                    </p>
                </div>
                <div class="card-meta">
                    <div>
                        <span class="source-name">📺 {row.get('video_title', '').split(':')[0][:20]}</span>
                    </div>
                    <div>
                        📅 {row['published_at'].strftime('%d %b %Y')}
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <a href="{row.get('video_url', '#')}" target="_blank" style="text-decoration: none;">
                        <button style="width:100%; border-radius:10px; border:1px solid #FF923B; background:transparent; color:#FF923B; padding:5px; font-weight:700; cursor:pointer;">
                            READ FULL ANALYSIS
                        </button>
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- BOTTONE REFRESH IN FONDO ---
st.markdown("<br><br>", unsafe_allow_html=True)
if st.button("🔄 REFRESH ALL DATA", use_container_width=True):
    st.rerun()