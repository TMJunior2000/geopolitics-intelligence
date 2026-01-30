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
    """Renderizza la card iniettando i dati nei template HTML esterni."""
    
    # 1. Preparazione Dati (Gestione robusta di None)
    style = row.get('channel_style') or 'Fondamentale'
    raw_rec = row.get('recommendation')
    rec = str(raw_rec).upper() if raw_rec else 'WATCH'
    rec_class = _get_badge_class(raw_rec)
    
    ticker = row.get('asset_ticker', 'ASSET')
    name = row.get('asset_name', '')
    summary = row.get('summary_card') or 'Nessun dettaglio disponibile.'
    drivers = row.get('key_drivers') or [] # Assicura che sia una lista
    video_url = row.get('video_url', '#')

    # Dati Tecnici
    entry = row.get('entry_zone')
    target = row.get('target_price')
    stop = row.get('stop_invalidation')
    horizon = row.get('time_horizon')
    
    # Determina se mostrare il box tecnico
    show_tech = any([entry, target, stop])

    # 2. Rendering Visuale
    with st.container(border=True):
        
        # A. Render Badges (Safe Jinja)
        html_badges = _safe_render_template("badges.html", style=style, rec=rec, rec_class=rec_class)
        st.markdown(html_badges, unsafe_allow_html=True)

        # B. Ticker e Nome
        st.markdown(f"### {ticker}")
        if name:
            st.caption(name)
        
        st.markdown("---")
        
        # C. Summary e Drivers
        st.markdown(f"**Analisi:** {summary}")
        if isinstance(drivers, list) and drivers:
            st.markdown("**Key Drivers:**")
            for driver in drivers:
                st.markdown(f"- {driver}")

        # D. Render Tech Box
        if show_tech:
            html_tech = _safe_render_template("tech_box.html",
                entry=entry or '-',
                target=target or '-',
                stop=stop or '-',
                horizon=horizon or '-'
            )
            st.markdown(html_tech, unsafe_allow_html=True)

        # E. Bottone
        if video_url and str(video_url).strip() != '#' and str(video_url).startswith('http'):
            st.markdown("") 
            st.link_button("📺 VEDI ANALISI", video_url, use_container_width=True)


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