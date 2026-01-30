import streamlit as st
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# --- CONFIGURAZIONE PERCORSI E JINJA ---
CURRENT_DIR = Path(__file__).parent.resolve()
# Risaliamo per trovare la cartella templates corretta
PROJECT_ROOT = CURRENT_DIR.parent.parent 
TEMPLATES_DIR = PROJECT_ROOT / "frontend" / "assets" / "templates"

# Setup Ambiente Jinja Sicuro (Protezione XSS)
# Se la cartella non esiste, evitiamo crash immediati, gestiremo l'errore al render
try:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(['html', 'xml']) # <-- FONDAMENTALE PER SICUREZZA
    )
except Exception:
    env = None

def _get_badge_class(rec):
    """Logica pura Python: decide la classe CSS in base al valore."""
    if not rec:
        return "badge-style"
        
    rec_upper = str(rec).strip().upper()
    cls_map = {
        "LONG": "badge-long",
        "SHORT": "badge-short",
        "WATCH": "badge-watch"
    }
    return cls_map.get(rec_upper, "badge-style")

def _safe_render_template(template_name, **kwargs):
    """Wrapper sicuro per renderizzare template o fallire con grazia."""
    if env is None:
        return ""
    
    try:
        template = env.get_template(template_name)
        return template.render(**kwargs)
    except Exception as e:
        # In sviluppo mostra l'errore, in prod potresti volerlo nascondere
        return f""
    
def _render_single_card(row):
    # 1. Gestione Colore e Tipo (Dati dal DB)
    channel_name = row.get('source_name', '')
    asset_style = row.get('channel_style', 'N.D.')
    sentiment = row.get('sentiment', 'N.D.')
    recommendation = row.get('recommendation', 'WATCH')
    
    # Colore bordo in base al canale
    accent_color = "#34495e" 
    if "investire biz" in channel_name.lower():
        accent_color = "#2ecc71"  # Verde
    elif "marketmind" in channel_name.lower():
        accent_color = "#95a5a6"  # Grigio

    # 2. Formattazione Data
    raw_date = row.get('published_at')
    display_date = "Data N.D."
    if raw_date:
        try:
            if hasattr(raw_date, 'strftime'):
                display_date = raw_date.strftime("%d/%m/%Y")
            else:
                import pandas as pd
                display_date = pd.to_datetime(raw_date).strftime("%d/%m/%Y")
        except Exception:
            display_date = str(raw_date)[:10]

    # 3. Rendering Card
    with st.container(border=True):
        # Header: Data e Ticker con bordo colorato del canale
        st.markdown(f"""
            <div style="border-left: 5px solid {accent_color}; padding-left: 10px; margin-bottom: 15px;">
                <span style="color: #888; font-size: 0.8rem;">📅 {display_date}</span>
                <h3 style="margin: 0;">{row.get('asset_ticker')}</h3>
                <span style="font-size: 0.85rem; opacity: 0.8;">🛠️ {asset_style}</span>
            </div>
        """, unsafe_allow_html=True)

        # Info Sentiment e Recommendation
        col_a, col_b = st.columns(2)
        col_a.caption("Sentiment")
        col_a.markdown(f"**{sentiment}**")
        col_b.caption("Recommendation")
        col_b.markdown(f"**{recommendation}**")

        st.markdown("---")

        # Bottone Dettagli
        if st.button("🔍 DETTAGLI COMPLETI", key=f"details_{row['id']}", use_container_width=True):
            _show_full_analysis_modal(row)

@st.dialog("Dettaglio Analisi")
def _show_full_analysis_modal(row):
    st.subheader(f"{row['asset_ticker']} - {row.get('asset_name', '')}")
    
    # Visualizzazione dei Key Drivers all'interno del dettaglio
    drivers = row.get('key_drivers')
    if drivers and isinstance(drivers, list):
        st.markdown("### 🎯 Key Drivers")
        drivers_html = "".join([f"<li style='margin-bottom: 5px;'>{d}</li>" for d in drivers])
        st.markdown(f"<ul style='padding-left: 20px;'>{drivers_html}</ul>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📝 Analisi Completa")
    st.write(row.get('video_summary') or row.get('summary_card'))
    
    if row.get('video_url'):
        st.divider()
        st.link_button("📺 Guarda Video Originale", row['video_url'], use_container_width=True)

def render_grid(df, assets_to_show):
    """Funzione principale chiamata dalla dashboard"""
    if df.empty:
        return

    # Ordinamento sicuro
    if 'published_at' in df.columns:
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