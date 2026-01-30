import streamlit as st
import os
from jinja2 import Template

# --- FUNZIONI DI UTILITÀ PER I TEMPLATE ---
def load_template(filename):
    """Carica un file HTML dalla cartella templates."""
    # Costruiamo il percorso assoluto o relativo sicuro
    path = os.path.join("frontend", "assets", "templates", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return Template(f.read())
    except FileNotFoundError:
        st.error(f"⚠️ Template non trovato: {path}")
        return None

# Carichiamo i template una volta sola all'avvio del modulo per performance
TEMPLATE_BADGES = load_template("badges.html")
TEMPLATE_TECH_BOX = load_template("tech_box.html")

def _get_badge_class(rec):
    """Logica pura Python: decide la classe CSS in base al valore."""
    rec = rec.upper()
    cls_map = {
        "LONG": "badge-long",
        "SHORT": "badge-short",
        "WATCH": "badge-watch"
    }
    return cls_map.get(rec, "badge-style")

def _render_single_card(row):
    """Renderizza la card iniettando i dati nei template HTML esterni."""
    
    # 1. Preparazione Dati (Logica)
    style = row.get('channel_style', 'Fondamentale')
    rec = str(row.get('recommendation', 'WATCH')).upper()
    rec_class = _get_badge_class(rec)
    
    ticker = row.get('asset_ticker', 'ASSET')
    name = row.get('asset_name', '')
    summary = row.get('summary_card', 'Nessun dettaglio disponibile.')
    drivers = row.get('key_drivers', [])
    video_url = row.get('video_url', '#')

    # Dati Tecnici
    entry = row.get('entry_zone')
    target = row.get('target_price')
    stop = row.get('stop_invalidation')
    horizon = row.get('time_horizon')
    
    # Determina se mostrare il box tecnico
    show_tech = any([entry, target, stop])

    # 2. Rendering Visuale (Streamlit + HTML Templates)
    with st.container(border=True):
        
        # A. Render Badges (usando il template)
        if TEMPLATE_BADGES:
            html_badges = TEMPLATE_BADGES.render(
                style=style, 
                rec=rec, 
                rec_class=rec_class
            )
            st.markdown(html_badges, unsafe_allow_html=True)

        # B. Ticker e Nome (Nativo Streamlit)
        st.markdown(f"### {ticker}")
        if name:
            st.caption(name)
        
        st.markdown("---")
        
        # C. Summary e Drivers (Nativo Streamlit)
        st.markdown(f"**Analisi:** {summary}")
        if drivers:
            st.markdown("**Key Drivers:**")
            for driver in drivers:
                st.markdown(f"- {driver}")

        # D. Render Tech Box (usando il template solo se serve)
        if show_tech and TEMPLATE_TECH_BOX:
            html_tech = TEMPLATE_TECH_BOX.render(
                entry=entry or '-',
                target=target or '-',
                stop=stop or '-',
                horizon=horizon or '-'
            )
            st.markdown(html_tech, unsafe_allow_html=True)

        # E. Bottone (Nativo Streamlit)
        if video_url and video_url != '#':
            st.markdown("") 
            st.link_button("📺 VEDI ANALISI", video_url, use_container_width=True)


def render_grid(df, assets_to_show):
    """Funzione principale chiamata dalla dashboard"""
    if not df.empty and 'published_at' in df.columns:
        df = df.sort_values(by='published_at', ascending=False)
    
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty: continue
        
        st.markdown(f"### 💎 {asset}")
        st.markdown("---")
        
        cols = st.columns(3)
        for idx, (_, row) in enumerate(asset_df.iterrows()):
            with cols[idx % 3]:
                _render_single_card(row)
        
        st.markdown("<br>", unsafe_allow_html=True)