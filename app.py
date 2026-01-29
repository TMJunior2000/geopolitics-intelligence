import streamlit as st
import pandas as pd
import requests
from streamlit_lottie import st_lottie
from services.db_service import DBService

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Trading Intelligence",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 1. CARICAMENTO ANIMAZIONI CON FALLBACK ---
@st.cache_resource # Usiamo cache_resource per caricare le animazioni una sola volta
def load_lottie_safe(url: str):
    try:
        # Timeout breve per non bloccare l'app se il sito è giù
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

lottie_rocket = load_lottie_safe("https://assets9.lottiefiles.com/packages/lf20_96bovgqk.json")
lottie_bear = load_lottie_safe("https://assets10.lottiefiles.com/packages/lf20_qpwbv5gm.json")

# --- 2. CSS CUSTOM (SOFT & ROUNDED) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; background-color: #FAFAFA; color: #1E1E1E; }
    .highlight-orange { color: #FF923B; font-weight: 800; }
    .modern-card { background: white; border-radius: 25px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #F0F0F0; }
    .pill-tag { display: inline-block; padding: 5px 15px; border-radius: 50px; font-size: 12px; font-weight: 700; margin-right: 5px; }
    .tag-bullish { background-color: #E8F5E9; color: #2E7D32; }
    .tag-bearish { background-color: #FFEBEE; color: #C62828; }
    .tag-asset { background-color: #FFF3E0; color: #EF6C00; }
    .img-overlay-container { position: relative; border-radius: 20px; overflow: hidden; height: 160px; width: 100%; margin-bottom: 15px; background-color: #eee; }
    .img-bg { width: 100%; height: 100%; object-fit: cover; }
    .overlay-gradient { position: absolute; bottom: 0; left: 0; width: 100%; height: 60%; background: linear-gradient(to top, rgba(0,0,0,0.7), transparent); }
</style>
""", unsafe_allow_html=True)

# --- 3. HELPER FUNCTIONS ---
def highlight_title(text):
    for k in ["Bitcoin", "Crypto", "Gold", "Oro", "Dollar", "Trump", "AI"]:
        text = text.replace(k, f'<span class="highlight-orange">{k}</span>')
    return text

def render_custom_card(insight):
    sentiment = str(insight.get('sentiment', 'NEUTRAL'))
    tag_class = "tag-bullish" if sentiment == "BULLISH" else "tag-bearish" if sentiment == "BEARISH" else "tag-neutral"
    icon = "🚀 BULL" if sentiment == "BULLISH" else "🐻 BEAR" if sentiment == "BEARISH" else "⚖️ NEUT"
    
    vid_id = insight.get('raw_metadata', {}).get('vid', '')
    img_url = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg" if vid_id else ""

    st.markdown(f"""
    <div class="modern-card">
        <div class="img-overlay-container">
            <img src="{img_url}" class="img-bg">
            <div class="overlay-gradient"></div>
        </div>
        <div style="margin-bottom: 10px;">
            <span class="pill-tag tag-asset">{insight.get('asset_ticker', 'N/A')}</span>
            <span class="pill-tag {tag_class}">{icon}</span>
        </div>
        <h3 style="font-size: 18px; margin: 0;">{highlight_title(insight.get('video_title', 'No Title'))}</h3>
        <p style="font-size: 14px; color: #666; margin-top: 10px;">{insight.get('ai_reasoning', '')[:100]}...</p>
    </div>
    """, unsafe_allow_html=True)

# --- 4. DATA LOGIC ---
db = DBService()
raw_data = db.get_all_insights_dataframe()
df = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()

# --- 5. UI LAYOUT ---
st.markdown("<h1>Trading<span class='highlight-orange'>Intelligence</span></h1>", unsafe_allow_html=True)

if not df.empty:
    df['published_at'] = pd.to_datetime(df['published_at'])
    
    # Navigation a pillole
    assets = ["ALL"] + sorted(df['asset_ticker'].unique().tolist())
    selected_asset = st.selectbox("Seleziona Asset", assets, label_visibility="collapsed")
    
    filtered_df = df if selected_asset == "ALL" else df[df['asset_ticker'] == selected_asset]

    # --- SPOTLIGHT CON PROTEZIONE TOTALE ---
    top_pick = filtered_df[filtered_df['sentiment'].isin(['BULLISH', 'BEARISH'])].head(1)
    
    if not top_pick.empty:
        p = top_pick.iloc[0]
        st.markdown("### ⚡ Daily Spotlight")
        c_text, c_anim = st.columns([2, 1])
        
        with c_text:
            st.info(f"**{p['asset_ticker']}**: {p['ai_reasoning']}")
            if p['key_levels']: st.code(f"Target Levels: {p['key_levels']}")
            
        with c_anim:
            # LOGICA DI PROTEZIONE: Se il JSON è None, non chiamare st_lottie
            sent = p['sentiment']
            if sent == "BULLISH":
                if lottie_rocket is not None:
                    st_lottie(lottie_rocket, height=150, key="anim_bull")
                else:
                    st.markdown("<h1 style='font-size:80px;'>🚀</h1>", unsafe_allow_html=True)
            elif sent == "BEARISH":
                if lottie_bear is not None:
                    st_lottie(lottie_bear, height=150, key="anim_bear")
                else:
                    st.markdown("<h1 style='font-size:80px;'>🐻</h1>", unsafe_allow_html=True)

    # --- GRID FEED ---
    st.markdown("### 📱 Latest Feed")
    grid_cols = st.columns(3)
    for i, (_, row) in enumerate(filtered_df.iterrows()):
        with grid_cols[i % 3]:
            render_custom_card(row)
else:
    st.info("Nessun dato disponibile. Avvia il backend.")

# Bottone refresh flottante (opzionale)
if st.button("🔄 AGGIORNA FEED", use_container_width=True):
    st.rerun()