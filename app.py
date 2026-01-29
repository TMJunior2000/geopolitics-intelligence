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
    initial_sidebar_state="collapsed"
)

# --- 1. CARICAMENTO ASSET (LOTTIE con Error Handling) ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

# Carichiamo le animazioni
lottie_rocket = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_96bovgqk.json")
lottie_bear = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_qpwbv5gm.json")

# --- 2. CSS INJECTION ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif;
        background-color: #FAFAFA;
        color: #1E1E1E;
    }

    .highlight-orange { color: #FF923B; font-weight: 800; }

    .modern-card {
        background: white;
        border-radius: 25px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #F0F0F0;
    }

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
    .tag-asset { background-color: #FFF3E0; color: #EF6C00; }

    .img-overlay-container {
        position: relative;
        border-radius: 20px;
        overflow: hidden;
        height: 180px;
        width: 100%;
        margin-bottom: 15px;
    }
    .img-bg { width: 100%; height: 100%; object-fit: cover; }
    .overlay-gradient {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 60%;
        background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def highlight_title(text):
    keywords = ["Bitcoin", "Crypto", "Gold", "Oro", "Dollar", "Trump", "AI", "Nucleare"]
    for k in keywords:
        text = text.replace(k, f'<span class="highlight-orange">{k}</span>')
    return text

def render_custom_card(insight):
    sentiment = str(insight.get('sentiment', 'NEUTRAL'))
    if sentiment == "BULLISH":
        tag_class, icon = "tag-bullish", "🚀 BULL"
    elif sentiment == "BEARISH":
        tag_class, icon = "tag-bearish", "🐻 BEAR"
    else:
        tag_class, icon = "tag-neutral", "⚖️ NEUT"

    vid_id = insight.get('raw_metadata', {}).get('vid', '')
    img_url = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg" if vid_id else ""
    
    card_html = f"""
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
        <p style="font-size: 14px; color: #666;">{insight.get('ai_reasoning', '')[:120]}...</p>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# --- DATA LOADING ---
db = DBService()
raw_data = db.get_all_insights_dataframe()
df = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()

if not df.empty:
    df['published_at'] = pd.to_datetime(df['published_at'])

# --- APP LAYOUT ---
st.markdown("<h1 style='font-size: 40px;'>Trading<span class='highlight-orange'>Intelligence</span></h1>", unsafe_allow_html=True)

if not df.empty:
    # Asset Selection
    assets = ["ALL"] + sorted(df['asset_ticker'].unique().tolist())
    # Risolviamo il warning del label vuoto
    selected_asset = st.selectbox("Select Asset Focus", assets, label_visibility="collapsed")

    filtered_df = df if selected_asset == "ALL" else df[df['asset_ticker'] == selected_asset]

    # SPOTLIGHT (Animazioni con protezione NoneType)
    top_pick = filtered_df[filtered_df['sentiment'].isin(['BULLISH', 'BEARISH'])].head(1)
    if not top_pick.empty:
        p = top_pick.iloc[0]
        c_text, c_anim = st.columns([2, 1])
        with c_text:
            st.markdown(f"### ⚡ Spotlight: {p['asset_ticker']}")
            st.info(p['ai_reasoning'])
        with c_anim:
            # PROTEZIONE CRUCIALE: se l'animazione è None, non carichiamo st_lottie
            if p['sentiment'] == "BULLISH" and lottie_rocket:
                st_lottie(lottie_rocket, height=150, key="rocket_anim")
            elif p['sentiment'] == "BEARISH" and lottie_bear:
                st_lottie(lottie_bear, height=150, key="bear_anim")

    # GRID
    st.markdown("### 📱 Latest Feed")
    cols = st.columns(3)
    for i, (_, row) in enumerate(filtered_df.iterrows()):
        with cols[i % 3]:
            render_custom_card(row)
else:
    st.info("No data found.")