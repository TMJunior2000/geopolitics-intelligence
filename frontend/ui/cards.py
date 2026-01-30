import streamlit as st
import os
from jinja2 import Template

# --- CONFIGURAZIONE ---
def load_template(filename):
    path = os.path.join("frontend", "assets", "templates", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return Template(f.read())
    except FileNotFoundError:
        return None

TEMPLATE_GENZ = load_template("card.html")

# --- PALETTE COLORI GEN Z ---
# Mappiamo i canali/asset ai colori HEX
COLOR_MAP = {
    # Crypto (Viola/Blu Elettrico)
    "BTC": "#8B5CF6", "ETH": "#6366F1", "SOL": "#14F195", "CRYPTO": "#8B5CF6",
    
    # Forex (Verde/Lime)
    "EURUSD": "#84CC16", "FOREX": "#10B981", 
    
    # Azioni/Indici (Arancione/Giallo)
    "SP500": "#F59E0B", "NASDAQ": "#F43F5E", "TSLA": "#EF4444", "STOCKS": "#F97316",
    
    # Commodities (Oro/Giallo)
    "GOLD": "#EAB308", "OIL": "#000000",
    
    # Default
    "DEFAULT": "#3B82F6" # Blu brillante
}

def _get_color_by_asset(ticker, channel_style):
    """
    Restituisce un colore HEX in base al ticker o allo stile del canale.
    """
    ticker = str(ticker).upper()
    style = str(channel_style).upper()
    
    # 1. Cerca per Ticker esatto
    if ticker in COLOR_MAP: return COLOR_MAP[ticker]
    
    # 2. Cerca per parole chiave nel ticker
    if "USD" in ticker: return COLOR_MAP["FOREX"]
    
    # 3. Cerca per Stile Canale
    if "CRYPTO" in style: return COLOR_MAP["CRYPTO"]
    if "FOREX" in style: return COLOR_MAP["FOREX"]
    if "AZION" in style or "STOCK" in style: return COLOR_MAP["STOCKS"]
    
    return COLOR_MAP["DEFAULT"]

def _get_image_url(ticker):
    """
    Genera un'immagine placeholder carina se manca quella reale.
    Usa un servizio esterno (come Unsplash source) per demo.
    """
    # In produzione useresti row.get('image_url') dal database
    keywords = {
        "BTC": "bitcoin", "ETH": "ethereum", "GOLD": "gold-bars", 
        "TSLA": "tesla-car", "EURUSD": "money"
    }
    keyword = keywords.get(ticker, "finance-chart")
    return f"https://source.unsplash.com/400x300/?{keyword}"

def _render_single_card(row):
    """Renderizza la card stile Gen Z."""
    
    # Estrazione Dati
    ticker = row.get('asset_ticker', 'ASSET')
    channel = row.get('channel_style', 'General')
    color = _get_color_by_asset(ticker, channel)
    
    # URL Immagine: Se nel DB hai un campo 'thumbnail', usa quello. 
    # Altrimenti uso un placeholder dinamico per l'effetto visivo
    img_url = row.get('thumbnail_url') 
    if not img_url:
        img_url = f"https://placehold.co/600x400/{color[1:]}/FFFFFF/png?text={ticker}"

    # Dati Tecnici
    entry = row.get('entry_zone')
    target = row.get('target_price')
    
    context = {
        "ticker": ticker,
        "name": row.get('asset_name', ''),
        "summary": row.get('summary_card', 'Nessuna descrizione.'),
        "rec": str(row.get('recommendation', 'WATCH')).upper(),
        "channel": channel,
        "color": color, # <-- IL COLORE DINAMICO
        "image_url": img_url,
        "video_url": row.get('video_url', '#'),
        "entry": entry,
        "target": target,
        "show_tech": bool(entry or target)
    }

    if TEMPLATE_GENZ:
        # Render HTML
        html = TEMPLATE_GENZ.render(**context)
        # In Streamlit, renderizziamo HTML puro senza container nativi
        # per avere il controllo totale del CSS (hover, shadows, borders)
        st.markdown(html, unsafe_allow_html=True)

def render_grid(df, assets_to_show):
    """Griglia responsive"""
    if not df.empty and 'published_at' in df.columns:
        df = df.sort_values(by='published_at', ascending=False)
    
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty: continue
        
        # Header Sezione con colore coordinato
        color = _get_color_by_asset(asset, "")
        st.markdown(f"""
            <h2 style='border-left: 4px solid {color}; padding-left: 10px; margin-top: 40px;'>
                {asset}
            </h2>
        """, unsafe_allow_html=True)
        
        # Grid layout
        cols = st.columns(3)
        for idx, (_, row) in enumerate(asset_df.iterrows()):
            with cols[idx % 3]:
                _render_single_card(row)
                # Spaziatore verticale tra le card nella stessa colonna
                st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)