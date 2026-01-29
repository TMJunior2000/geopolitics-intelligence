import streamlit as st
import pandas as pd
import requests
from streamlit_lottie import st_lottie
from services.db_service import DBService

# --- CONFIGURAZIONE ---
st.set_page_config(
    page_title="Trading Intelligence",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="collapsed" # Nascondiamo la sidebar per un look più "App"
)

# --- 1. CARICAMENTO ASSET (LOTTIE & FONT) ---
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200: return None
    return r.json()

# Animazione "Rocket" per il sentiment Bullish
lottie_rocket = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_96bovgqk.json")
# Animazione "Warning" per il sentiment Bearish
lottie_bear = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_qpwbv5gm.json")

# --- 2. CSS INJECTION (IL MOTORE GRAFICO) ---
st.markdown("""
<style>
    /* IMPORT FONT 'QUICKSAND' (Simile ad Avocado) */
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');

    /* BASE STYLES */
    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif;
        background-color: #FAFAFA; /* Bianco sporco morbido */
        color: #1E1E1E;
    }

    /* NASCONDE ELEMENTI STANDARD BRUTTI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* TITOLI */
    h1, h2, h3 {
        color: #1E1E1E;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .highlight-orange {
        color: #FF923B;
        font-weight: 800;
    }

    /* CARD DESIGN (Soft & Rounded) */
    .modern-card {
        background: white;
        border-radius: 25px; /* Arrotondamento estremo */
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); /* Ombra soffice */
        margin-bottom: 20px;
        transition: transform 0.2s ease;
        border: 1px solid #F0F0F0;
    }
    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(255, 146, 59, 0.15); /* Ombra arancione al passaggio */
        border-color: #FF923B;
    }

    /* BOTTONI A PILLOLA */
    .stButton button {
        border-radius: 50px !important;
        background-color: #FF923B !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 10px 25px !important;
        box-shadow: 0 4px 15px rgba(255, 146, 59, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        background-color: #1E1E1E !important; /* Diventa nero al passaggio */
        transform: scale(1.05) !important;
    }

    /* TAG / BADGES */
    .pill-tag {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 50px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 5px;
    }
    .tag-bullish { background-color: #E8F5E9; color: #2E7D32; }
    .tag-bearish { background-color: #FFEBEE; color: #C62828; }
    .tag-neutral { background-color: #F5F5F5; color: #616161; }
    .tag-asset { background-color: #FFF3E0; color: #EF6C00; }

    /* LAYOUT IMMAGINI CON OVERLAY */
    .img-overlay-container {
        position: relative;
        border-radius: 20px;
        overflow: hidden;
        height: 180px;
        width: 100%;
        margin-bottom: 15px;
    }
    .img-bg {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .overlay-gradient {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 60%;
        background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
    }
    .overlay-text {
        position: absolute;
        bottom: 15px;
        left: 15px;
        color: white;
        font-weight: 700;
        font-size: 14px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }

</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def highlight_title(text):
    """Colora di arancione parole chiave come Crypto, Gold, Bitcoin"""
    keywords = ["Bitcoin", "Crypto", "Gold", "Oro", "Dollar", "Trump", "AI", "Nucleare", "Azioni"]
    for k in keywords:
        text = text.replace(k, f'<span class="highlight-orange">{k}</span>')
    return text

def render_custom_card(insight):
    """Genera l'HTML per una card stile App."""
    
    # Colori e Icone dinamici
    if insight['sentiment'] == "BULLISH":
        tag_class = "tag-bullish"
        sentiment_icon = "🚀 BULL"
    elif insight['sentiment'] == "BEARISH":
        tag_class = "tag-bearish"
        sentiment_icon = "🐻 BEAR"
    else:
        tag_class = "tag-neutral"
        sentiment_icon = "⚖️ NEUT"

    vid_id = insight['raw_metadata'].get('vid', '')
    img_url = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg" if vid_id else "https://via.placeholder.com/400x200"
    
    # HTML STRUTTURA CARD
    card_html = f"""
    <div class="modern-card">
        <!-- HEADER IMMAGINE -->
        <div class="img-overlay-container">
            <img src="{img_url}" class="img-bg">
            <div class="overlay-gradient"></div>
            <div class="overlay-text">
                {insight['timeframe']} VIEW
            </div>
        </div>

        <!-- TAGS -->
        <div style="margin-bottom: 10px;">
            <span class="pill-tag tag-asset">{insight['asset_ticker']}</span>
            <span class="pill-tag {tag_class}">{sentiment_icon}</span>
        </div>

        <!-- CONTENUTO -->
        <h3 style="font-size: 18px; margin: 0 0 10px 0;">{highlight_title(insight['video_title'])}</h3>
        <p style="font-size: 14px; color: #666; line-height: 1.5;">
            {insight['ai_reasoning'][:120]}...
        </p>

        <!-- FOOTER -->
        <div style="margin-top: 15px; padding-top: 10px; border-top: 1px dashed #eee; font-size: 12px; color: #999; display: flex; justify-content: space-between;">
            <span>📅 {insight['published_at'].strftime('%d/%m')}</span>
            <a href="{insight['video_url']}" target="_blank" style="color: #FF923B; text-decoration: none; font-weight: bold;">WATCH ➜</a>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# --- LOAD DATA ---
db = DBService()
df = pd.DataFrame(db.get_all_insights_dataframe())
if not df.empty:
    df['published_at'] = pd.to_datetime(df['published_at'])

# --- HEADER APP (Titolo Grande) ---
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("""
    <h1 style="font-size: 48px; margin-bottom: 0;">Trading<span class="highlight-orange">Intelligence</span></h1>
    <p style="font-size: 18px; color: #888; margin-top: -10px;">Daily Insights for Gen Z Investors</p>
    """, unsafe_allow_html=True)
with c2:
    # Bottone refresh mascherato da pulsante app
    if st.button("🔄 REFRESH FEED"):
        st.cache_data.clear()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- FILTRI A PILLOLA (SCORRIMENTO ORIZZONTALE) ---
if not df.empty:
    assets = ["ALL"] + sorted(df['asset_ticker'].unique().tolist())
    
    # Usiamo le colonne per simulare una barra orizzontale
    st.write("🔥 **Trending Assets:**")
    cols = st.columns(len(assets) if len(assets) < 8 else 8)
    
    selected_asset = "ALL"
    # (Nota: Streamlit non gestisce benissimo la selezione a bottoni multipli senza session state, 
    # qui semplifichiamo con una selectbox stilizzata o usiamo radio orizzontale)
    selected_asset = st.selectbox("", assets, label_visibility="collapsed")

    # Filtro Dati
    if selected_asset != "ALL":
        filtered_df = df[df['asset_ticker'] == selected_asset]
    else:
        filtered_df = df

    st.markdown("<br>", unsafe_allow_html=True)

    # --- TOP STORY (Il Segnale più Forte) ---
    # Cerchiamo un segnale con sentiment forte recente
    top_picks = filtered_df[filtered_df['sentiment'].isin(['BULLISH', 'BEARISH'])].head(1)
    
    if not top_picks.empty:
        pick = top_picks.iloc[0]
        st.markdown("### ⚡ <span class='highlight-orange'>Daily</span> Spotlight", unsafe_allow_html=True)
        
        col_main, col_anim = st.columns([2, 1])
        with col_main:
            # Card Gigante per l'highlight
            st.markdown(f"""
            <div class="modern-card" style="border: 2px solid #FF923B; background: #FFF3E0;">
                <span class="pill-tag" style="background: #FF923B; color: white;">TOP PICK</span>
                <h2 style="font-size: 28px; margin-top: 10px;">{pick['asset_ticker']} è {pick['sentiment']}</h2>
                <p style="font-size: 16px;">{pick['ai_reasoning']}</p>
                <p class="highlight-orange" style="font-family: monospace;">TARGET LEVELS: {pick['key_levels']}</p>
            </div>
            """, unsafe_allow_html=True)
        with col_anim:
            if pick['sentiment'] == "BULLISH":
                st_lottie(lottie_rocket, height=200, key="rocket")
            else:
                st_lottie(lottie_bear, height=200, key="bear")

    # --- GRID LAYOUT (Le Card) ---
    st.markdown("### 📱 <span class='highlight-orange'>Latest</span> Feed", unsafe_allow_html=True)
    
    # Layout a 3 colonne responsive
    col1, col2, col3 = st.columns(3)
    
    for i, (_, row) in enumerate(filtered_df.iterrows()):
        # Distribuzione card nelle colonne basata sul contatore 'i'
        if i % 3 == 0:
            with col1: render_custom_card(row)
        elif i % 3 == 1:
            with col2: render_custom_card(row)
        else:
            with col3: render_custom_card(row)

else:
    st.info("Nessun dato. Lancia il worker per iniziare.")